#!/usr/bin/env python3
"""
Пример использования XG синтезатора в реальном приложении
"""

import numpy as np
import pygame
import pygame.midi
import time
import sys
import os

# Добавляем путь к директории с модулями
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from xg_synthesizer import XGSynthesizer


class XGMusicPlayer:
    \"\"\"Пример музыкального проигрывателя с XG синтезатором\"\"\"
    
    def __init__(self, sample_rate=44100, block_size=512):
        \"\"\"
        Инициализация музыкального проигрывателя
        
        Args:
            sample_rate: частота дискретизации
            block_size: размер аудио блока
        \"\"\"
        self.sample_rate = sample_rate
        self.block_size = block_size
        
        # Инициализируем Pygame mixer
        pygame.mixer.pre_init(frequency=sample_rate, size=-16, channels=2, buffer=block_size)
        pygame.mixer.init()
        pygame.midi.init()
        
        # Создаем синтезатор
        self.synth = XGSynthesizer(sample_rate=sample_rate, block_size=block_size)
        
        # Состояние проигрывателя
        self.is_playing = False
        self.current_song = None
        self.song_position = 0
        self.tempo = 120  # BPM
        
        print("XG Music Player инициализирован")
        print(f"Доступные MIDI устройства: {pygame.midi.get_count()}")
    
    def load_soundfonts(self, sf2_paths):
        \"\"\"
        Загрузка SoundFont файлов
        
        Args:
            sf2_paths: список путей к SF2 файлам
        \"\"\"
        print("Загрузка SoundFont файлов...")
        self.synth.set_sf2_files(sf2_paths)
        
        # Пример настройки черных списков и маппинга банков
        for sf2_path in sf2_paths:
            # Исключаем некоторые банки
            self.synth.set_bank_blacklist(sf2_path, [120, 121, 122])
            # Исключаем некоторые пресеты
            self.synth.set_preset_blacklist(sf2_path, [(0, 30), (0, 31)])
            # Настройка маппинга банков
            self.synth.set_bank_mapping(sf2_path, {1: 0, 2: 1})
    
    def connect_midi_device(self, device_id=None):
        \"\"\"
        Подключение MIDI устройства
        
        Args:
            device_id: ID устройства (если None, используем первое доступное)
        \"\"\"
        if device_id is None:
            # Ищем первое доступное устройство ввода
            for i in range(pygame.midi.get_count()):
                info = pygame.midi.get_device_info(i)
                if info and info[2] == 1:  # Входное устройство
                    device_id = i
                    break
        
        if device_id is not None:
            try:
                self.midi_input = pygame.midi.Input(device_id)
                device_info = pygame.midi.get_device_info(device_id)
                print(f"Подключено MIDI устройство: {device_info[1].decode('utf-8')}")
                return True
            except Exception as e:
                print(f"Ошибка подключения MIDI устройства: {e}")
        
        print("Не удалось подключить MIDI устройство")
        return False
    
    def play_note(self, note, velocity=100, channel=0, duration=1.0):
        \"\"\"
        Проигрывание ноты
        
        Args:
            note: MIDI нота (0-127)
            velocity: громкость (0-127)
            channel: MIDI канал (0-15)
            duration: длительность в секундах
        \"\"\"
        print(f"Проигрывание ноты {note} (канал {channel}), громкость {velocity}")
        
        # Отправляем Note On
        self.synth.send_midi_message(0x90 + channel, note, velocity)
        
        # Ждем заданное время
        time.sleep(duration)
        
        # Отправляем Note Off
        self.synth.send_midi_message(0x80 + channel, note, 64)
    
    def play_chord(self, notes, velocity=100, channel=0, duration=1.0):
        \"\"\"
        Проигрывание аккорда
        
        Args:
            notes: список MIDI нот
            velocity: громкость (0-127)
            channel: MIDI канал (0-15)
            duration: длительность в секундах
        \"\"\"
        print(f"Проигрывание аккорда {notes} (канал {channel})")
        
        # Отправляем Note On для всех нот
        for note in notes:
            self.synth.send_midi_message(0x90 + channel, note, velocity)
        
        # Ждем заданное время
        time.sleep(duration)
        
        # Отправляем Note Off для всех нот
        for note in notes:
            self.synth.send_midi_message(0x80 + channel, note, 64)
    
    def play_scale(self, root_note=60, scale_type="major", channel=0):
        \"\"\"
        Проигрывание гаммы
        
        Args:
            root_note: тоника гаммы
            scale_type: тип гаммы ("major" или "minor")
            channel: MIDI канал
        \"\"\"
        # Определяем интервалы для гаммы
        if scale_type == "major":
            intervals = [0, 2, 4, 5, 7, 9, 11, 12]  # мажорная гамма
        elif scale_type == "minor":
            intervals = [0, 2, 3, 5, 7, 8, 10, 12]  # минорная гамма
        else:
            intervals = [0, 2, 4, 5, 7, 9, 11, 12]  # по умолчанию мажор
        
        print(f"Проигрывание {scale_type} гаммы от ноты {root_note}")
        
        # Проигрываем каждую ноту гаммы
        for i, interval in enumerate(intervals):
            note = root_note + interval
            self.play_note(note, velocity=80, channel=channel, duration=0.5)
            time.sleep(0.1)  # пауза между нотами
    
    def process_midi_input(self):
        \"\"\"Обработка входящих MIDI сообщений\"\"\"
        if hasattr(self, 'midi_input') and self.midi_input.poll():
            midi_events = self.midi_input.read(10)  # Читаем до 10 событий
            
            for event in midi_events:
                data = event[0]
                timestamp = event[1]
                
                status = data[0]
                data1 = data[1]
                data2 = data[2]
                
                # Отправляем сообщение в синтезатор
                self.synth.send_midi_message(status, data1, data2)
    
    def generate_audio_stream(self, duration=10.0):
        \"\"\"
        Генерация аудио потока
        
        Args:
            duration: длительность в секундах
        \"\"\"
        print(f"Генерация аудио потока длительностью {duration} секунд...")
        
        # Вычисляем количество блоков
        blocks_per_second = self.sample_rate / self.block_size
        total_blocks = int(duration * blocks_per_second)
        
        # Создаем массив для аудио данных
        audio_data = []
        
        start_time = time.time()
        
        for i in range(total_blocks):
            # Обрабатываем входящие MIDI сообщения
            self.process_midi_input()
            
            # Генерируем аудио блок
            left_channel, right_channel = self.synth.generate_audio_block(self.block_size)
            
            # Конвертируем в 16-битные значения
            left_int16 = (left_channel * 32767).astype(np.int16)
            right_int16 = (right_channel * 32767).astype(np.int16)
            
            # Интерливинг каналов (LRLRLR...)
            interleaved = np.empty((left_int16.size + right_int16.size,), dtype=np.int16)
            interleaved[0::2] = left_int16
            interleaved[1::2] = right_int16
            
            audio_data.append(interleaved)
        
        end_time = time.time()
        print(f"Сгенерировано {total_blocks} блоков за {end_time - start_time:.2f} секунд")
        
        return np.concatenate(audio_data)
    
    def play_demo(self):
        \"\"\"Демонстрационное проигрывание\"\"\"
        print("=== Демонстрация XG синтезатора ===")
        
        # Установка программы
        print("Установка программы пианино...")
        self.synth.send_midi_message(0xC0, 0)  # Программа 0 (пианино)
        
        # Проигрывание мажорной гаммы
        self.play_scale(root_note=60, scale_type="major", channel=0)
        
        time.sleep(1)
        
        # Проигрывание минорной гаммы
        print("Установка программы органа...")
        self.synth.send_midi_message(0xC0, 19)  # Программа 19 (орган)
        
        self.play_scale(root_note=60, scale_type="minor", channel=0)
        
        time.sleep(1)
        
        # Проигрывание аккордов
        print("Проигрывание аккордов...")
        c_major = [60, 64, 67]  # До мажор
        f_major = [65, 69, 72]  # Фа мажор
        g_major = [67, 71, 74]  # Соль мажор
        
        chords = [c_major, f_major, g_major, c_major]
        
        for chord in chords:
            self.play_chord(chord, velocity=90, channel=0, duration=0.8)
            time.sleep(0.2)
        
        print("Демонстрация завершена!")
    
    def cleanup(self):
        \"\"\"Очистка ресурсов\"\"\"
        if hasattr(self, 'midi_input'):
            self.midi_input.close()
        
        pygame.midi.quit()
        pygame.mixer.quit()
        
        print("Ресурсы освобождены")


def main():
    \"\"\"Основная функция\"\"\"
    print("XG Music Player Demo")
    print("=" * 30)
    
    try:
        # Создаем проигрыватель
        player = XGMusicPlayer(sample_rate=44100, block_size=512)
        
        # Загружаем SoundFont файлы (укажите реальные пути)
        # player.load_soundfonts([
        #     "path/to/FluidR3_GM.sf2",
        #     "path/to/GeneralUserGS.sf2"
        # ])
        
        # Подключаем MIDI устройство (если доступно)
        # player.connect_midi_device()
        
        # Запускаем демонстрацию
        player.play_demo()
        
        # Генерируем аудио поток (пример)
        # audio_stream = player.generate_audio_stream(duration=5.0)
        # print(f"Сгенерирован аудио поток: {len(audio_stream)} сэмплов")
        
    except KeyboardInterrupt:
        print("\nПрервано пользователем")
    except Exception as e:
        print(f"Ошибка: {e}")
        import traceback
        traceback.print_exc()
    finally:
        if 'player' in locals():
            player.cleanup()


if __name__ == "__main__":
    main()