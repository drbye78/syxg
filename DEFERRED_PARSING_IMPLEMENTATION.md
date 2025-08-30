        return source_name
    
    def _normalize_modulator_amount(self, amount: int, destination: int) -> float:
        """
        Нормализация глубины модуляции в зависимости от цели с кэшированием.
        
        Args:
            amount: исходное значение глубины модуляции
            destination: цель модуляции
            
        Returns:
            нормализованное значение глубины модуляции
        """
        # Создаем кэш если он еще не существует
        if not hasattr(self, '_normalize_cache'):
            self._normalize_cache = {}
        
        # Генерируем ключ для кэширования
        cache_key = (amount, destination)
        
        # Проверяем кэш
        if cache_key in self._normalize_cache:
            return self._normalize_cache[cache_key]
        
        # Вычисляем нормализованное значение
        abs_amount = abs(amount)
        
        # Для pitch модуляции (в центах)
        if destination in [5, 6, 7]:
            result = abs_amount / 100.0  # 100 = 1 цент
        # Для cutoff фильтра
        elif destination in [8, 10, 11]:
            result = abs_amount / 1000.0  # Нормализуем к 0-1
        # Для амплитуды
        elif destination in [13, 31, 33, 34, 35]:
            result = abs_amount / 1000.0  # Нормализуем к 0-1
        # Для панорамирования
        elif destination == 17:
            result = abs_amount / 100.0  # 0-100 в SoundFont -> 0-1
        # Для трепета (tremolo)
        elif destination in [77, 78]:
            result = abs_amount / 1000.0  # Нормализуем к 0-1
        # Для других целей
        else:
            result = abs_amount / 1000.0  # Общая нормализация
        
        # Сохраняем в кэш
        self._normalize_cache[cache_key] = result
        return result
    
    def _build_global_preset_map(self):
        """Собираем все пресеты из всех SF2 файлов в один глобальный список с приоритетами"""
        # Очищаем глобальные структуры
        self.presets.clear()
        self.instruments.clear()
        self.sample_headers.clear()
        self.bank_instruments.clear()
        
        # Собираем все пресеты с учетом приоритетов
        all_presets = []
        
        for manager in self.sf2_managers:
            sf2_path = manager['path']
            
            # Получаем настройки для этого SF2 файла
            bank_blacklist = self.bank_blacklists.get(sf2_path, [])
            preset_blacklist = self.preset_blacklists.get(sf2_path, [])
            bank_mapping = self.bank_mappings.get(sf2_path, {})
            
            # Для отложенной загрузки мы не парсим все пресеты сразу,
            # а помечаем, что они будут загружены по запросу
            manager['deferred_presets_loaded'] = False
            
            # Добавляем информацию о файле в глобальную карту
            # Реальные пресеты будут загружены при первом обращении
            self.bank_instruments[sf2_path] = {
                'manager': manager,
                'bank_mapping': bank_mapping,
                'bank_blacklist': bank_blacklist,
                'preset_blacklist': preset_blacklist
            }
    
    def _load_presets_for_manager(self, manager: Dict[str, Any]):
        """Загружает пресеты для конкретного менеджера при необходимости"""
        if manager.get('deferred_presets_loaded', False):
            return
            
        try:
            # Гарантируем, что менеджер полностью распарсен
            self._ensure_manager_parsed(manager)
            manager['deferred_presets_loaded'] = True
        except Exception as e:
            print(f"Ошибка при загрузке пресетов для {manager['path']}: {str(e)}")
            manager['deferred_presets_loaded'] = True  # Помечаем как загруженный даже в случае ошибки

    def _find_preset_index(self, program: int, bank: int) -> Optional[int]:
        """
        Находит индекс пресета по программе и банку с отложенной загрузкой.
        
        Args:
            program: номер программы (0-127)
            bank: номер банка (0-16383)
            
        Returns:
            индекс пресета или None
        """
        # Проверяем каждый менеджер на наличие нужного пресета
        for manager in self.sf2_managers:
            # Загружаем пресеты для менеджера, если они еще не загружены
            self._load_presets_for_manager(manager)
            
            # Ищем пресет в загруженных данных
            for i, preset in enumerate(manager['presets']):
                if preset.preset == program and preset.bank == bank:
                    return i
                    
        return None
    
    def get_program_parameters(self, program: int, bank: int = 0) -> dict:
        """
        Получение параметров программы в формате, совместимом с XGToneGenerator.
        Реализует отложенную загрузку - структуры SF2 парсятся только при фактическом запросе.
        
        Args:
            program: номер программы (0-127)
            bank: номер банка (0-16383)
            
        Returns:
            словарь с параметрами программы
        """
        # Найти пресет и его менеджер по банку и программе
        preset_manager = None
        preset_obj = None
        
        # Ищем пресет во всех менеджерах
        for manager in self.sf2_managers:
            # Загружаем пресеты для менеджера при необходимости
            self._load_presets_for_manager(manager)
            
            # Ищем нужный пресет
            for preset in manager['presets']:
                if preset.preset == program and preset.bank == bank:
                    preset_manager = manager
                    preset_obj = preset
                    break
            
            if preset_manager:
                break
        
        # Если пресет не найден, возвращаем параметры по умолчанию
        if not preset_manager or not preset_obj:
            return self._get_default_parameters()
        
        # Загружаем инструменты из соответствующего менеджера
        instruments = preset_manager['instruments']
        
        # Собрать все объединенные зоны для этого пресета
        all_merged_zones = []
        for preset_zone in preset_obj.zones:
            if preset_zone.instrument_index < len(instruments):
                instrument = instruments[preset_zone.instrument_index]
                # Объединяем параметры пресета и инструмента для каждой зоны
                for instrument_zone in instrument.zones:
                    merged_zone = self._merge_preset_and_instrument_params(preset_zone, instrument_zone)
                    all_merged_zones.append(merged_zone)
        
        # Если зон нет, возвращаем параметры по умолчанию
        if not all_merged_zones:
            return self._get_default_parameters()
        
        # Преобразуем зоны в параметры частичных структур
        partials_params = []
        for zone in all_merged_zones:
            partial_params = self._convert_zone_to_partial_params(zone)
            partials_params.append(partial_params)
        
        # Базовые параметры
        params = {
            "amp_envelope": self._calculate_average_envelope(
                [p["amp_envelope"] for p in partials_params]
            ),
            "filter_envelope": self._calculate_average_envelope(
                [p["filter_envelope"] for p in partials_params]
            ),
            "pitch_envelope": self._calculate_average_envelope(
                [p["pitch_envelope"] for p in partials_params]
            ),
            "filter": self._calculate_average_filter(
                [p["filter"] for p in partials_params]
            ),
            "lfo1": {
                "waveform": "sine",
                "rate": self._convert_lfo_rate(all_merged_zones[0].LFO1Freq),
                "depth": 0.5,
                "delay": self._convert_time_cents_to_seconds(all_merged_zones[0].DelayLFO1)
            },
            "lfo2": {
                "waveform": "triangle",
                "rate": self._convert_lfo_rate(all_merged_zones[0].LFO2Freq),
                "depth": 0.3,
                "delay": self._convert_time_cents_to_seconds(all_merged_zones[0].DelayLFO2)
            },
            "lfo3": {
                "waveform": "sawtooth",
                "rate": 0.5,
                "depth": 0.1,
                "delay": 0.5
            },
            "modulation": self._calculate_modulation_params(all_merged_zones),
            "partials": partials_params
        }
        
        return params
    
    def get_drum_parameters(self, note: int, program: int, bank: int = 128) -> dict:
        """
        Получение параметров барабана в формате, совместимом с XGToneGenerator.
        Реализует отложенную загрузку - структуры SF2 парсятся только при фактическом запросе.
        
        Args:
            note: MIDI нота (0-127)
            program: номер программы (обычно 0 для барабанов)
            bank: номер банка (обычно 128 для барабанов)
            
        Returns:
            словарь с параметрами барабана
        """
        # Для барабанов используем специальный банк (128)
        # Ищем пресет во всех менеджерах
        preset_manager = None
        preset_obj = None
        
        # Ищем пресет во всех менеджерах
        for manager in self.sf2_managers:
            # Загружаем пресеты для менеджера при необходимости
            self._load_presets_for_manager(manager)
            
            # Ищем нужный пресет для барабанов
            for preset in manager['presets']:
                if preset.preset == program and preset.bank == bank:
                    preset_manager = manager
                    preset_obj = preset
                    break
            
            if preset_manager:
                break
        
        # Если не найдено в банке 128, пробуем банк 0
        if not preset_manager:
            for manager in self.sf2_managers:
                self._load_presets_for_manager(manager)
                
                for preset in manager['presets']:
                    if preset.preset == program and preset.bank == 0:
                        preset_manager = manager
                        preset_obj = preset
                        break
                
                if preset_manager:
                    break
        
        # Если пресет не найден, возвращаем параметры по умолчанию
        if not preset_manager or not preset_obj:
            return self._get_default_drum_parameters(note)
        
        # Загружаем инструменты из соответствующего менеджера
        instruments = preset_manager['instruments']
        
        # Найти зоны, соответствующие этой ноте, и объединить параметры
        matching_merged_zones = []
        for preset_zone in preset_obj.zones:
            if preset_zone.lokey <= note <= preset_zone.hikey:
                if preset_zone.instrument_index < len(instruments):
                    instrument = instruments[preset_zone.instrument_index]
                    for instrument_zone in instrument.zones:
                        if instrument_zone.lokey <= note <= instrument_zone.hikey:
                            # Объединяем параметры пресета и инструмента
                            merged_zone = self._merge_preset_and_instrument_params(preset_zone, instrument_zone)
                            matching_merged_zones.append(merged_zone)
        
        # Если не найдено подходящих зон, возвращаем параметры по умолчанию
        if not matching_merged_zones:
            return self._get_default_drum_parameters(note)
        
        # Преобразуем зоны в параметры частичных структур
        partials_params = []
        for zone in matching_merged_zones:
            partial_params = self._convert_zone_to_partial_params(zone, is_drum=True)
            partial_params["key_range_low"] = note
            partial_params["key_range_high"] = note
            partials_params.append(partial_params)
        
        # Базовые параметры для барабанов
        params = {
            "amp_envelope": self._calculate_average_envelope(
                [p["amp_envelope"] for p in partials_params]
            ),
            "filter_envelope": self._calculate_average_envelope(
                [p["filter_envelope"] for p in partials_params]
            ),
            "pitch_envelope": self._calculate_average_envelope(
                [p["pitch_envelope"] for p in partials_params]
            ),
            "filter": self._calculate_average_filter(
                [p["filter"] for p in partials_params]
            ),
            "lfo1": {
                "waveform": "sine",
                "rate": 0.0,
                "depth": 0.0,
                "delay": 0.0
            },
            "lfo2": {
                "waveform": "sine",
                "rate": 0.0,
                "depth": 0.0,
                "delay": 0.0
            },
            "lfo3": {
                "waveform": "sine",
                "rate": 0.0,
                "depth": 0.0,
                "delay": 0.0
            },
            "modulation": self._calculate_modulation_params(matching_merged_zones),
            "partials": partials_params
        }
        
        return params