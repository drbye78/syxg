    
    def handle_xg_parameter_change(self, parameter_msb: int, parameter_lsb: int, value_msb: int, value_lsb: int):
        """
        Обработка XG Parameter Change сообщения.
        
        Args:
            parameter_msb: старший байт параметра
            parameter_lsb: младший байт параметра
            value_msb: старший байт значения
            value_lsb: младший байт значения
        """
        # 14-битное значение
        value = (value_msb << 7) | value_lsb
        
        # Обработка различных XG параметров
        if parameter_msb == 0x00 and parameter_lsb == 0x00:  # Pitch Bend Range
            self.pitch_bend_range = value / 100.0
        elif parameter_msb == 0x00 and parameter_lsb == 0x01:  # Fine Tuning
            self.fine_tuning = (value - 8192) * 100 / 16383.0
        elif parameter_msb == 0x00 and parameter_lsb == 0x02:  # Coarse Tuning
            self.coarse_tuning = value - 8192
        elif parameter_msb == 0x00 and parameter_lsb == 0x03:  # Master Tuning
            # Применяем мастер-настройку
            pass
        elif parameter_msb == 0x00 and parameter_lsb == 0x04:  # Master Volume
            self.master_volume = value / 16383.0
        # Добавьте другие параметры по необходимости
    
    def handle_xg_bulk_parameter_dump(self, bank: int, data_type: int, data: List[int]):
        """
        Обработка XG Bulk Parameter Dump сообщения.
        
        Args:
            bank: номер банка
            data_type: тип данных
            data: данные параметров
        """
        # Обработка в зависимости от типа данных
        if data_type == 0x00:  # Partial Parameters
            self._handle_bulk_partial(data)
        elif data_type == 0x01:  # Program Parameters
            self._handle_bulk_program(data)
        elif data_type == 0x02:  # Drum Kit Parameters
            self._handle_bulk_drum_kit(data)
        elif data_type == 0x03:  # System Parameters
            self._handle_bulk_system(data)
        elif data_type == 0x7F:  # All Parameters
            self._handle_bulk_all_parameters(data)
    
    def _handle_bulk_partial(self, data: List[int]):
        """Обработка bulk данных для частичной структуры"""
        pass  # Реализация зависит от структуры данных
    
    def _handle_bulk_program(self, data: List[int]):
        """Обработка bulk данных для программы"""
        pass  # Реализация зависит от структуры данных
    
    def _handle_bulk_drum_kit(self, data: List[int]):
        """Обработка bulk данных для барабанного набора"""
        pass  # Реализация зависит от структуры данных
    
    def _handle_bulk_system(self, data: List[int]):
        """Обработка bulk данных для системных параметров"""
        pass  # Реализация зависит от структуры данных
    
    def _handle_bulk_all_parameters(self, data: List[int]):
        """Обработка bulk данных для всех параметров"""
        pass  # Реализация зависит от структуры данных