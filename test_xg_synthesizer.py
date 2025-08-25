#!/usr/bin/env python3
"""
Тестовый скрипт для XG синтезатора
"""

import numpy as np
import time
import sys
import os

# Добавляем путь к директории с модулями
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from xg_synthesizer import XGSynthesizer


def test_basic_functionality():
    """Тест базовой функциональности синтезатора"""
    print("=== Тест базовой функциональности ===")
    
    # Создаем синтезатор
    synth = XGSynthesizer(sample_rate=44100, block_size=512, max_polyphony=32)
    
    # Проверяем установку SF2 файлов
    print("Установка SF2 файлов...")
    # В реальном приложении здесь будут реальные пути к SF2 файлам
    # synth.set_sf2_files(["path/to/soundfont.sf2"])
    
    # Проверяем базовые параметры
    print(f"Частота дискретизации: {synth.sample_rate} Гц")
    print(f"Размер блока: {synth.block_size} сэмплов")
    print(f"Максимальная полифония: {synth.max_polyphony} голосов")
    print(f"Мастер-громкость: {synth.master_volume}")
    
    # Проверяем отправку MIDI сообщений
    print("\nОтправка MIDI сообщений...")
    synth.send_midi_message(0x90, 60, 100)  # Note On: C4, velocity 100 на канале 0
    synth.send_midi_message(0x80, 60, 64)   # Note Off: C4 на канале 0
    
    # Проверяем генерацию аудио
    print("\nГенерация аудио блока...")
    left_channel, right_channel = synth.generate_audio_block(1024)
    print(f"Сгенерировано {len(left_channel)} сэмплов")
    print(f"Левый канал: мин={np.min(left_channel):.6f}, макс={np.max(left_channel):.6f}")
    print(f"Правый канал: мин={np.min(right_channel):.6f}, макс={np.max(right_channel):.6f}")
    
    # Проверяем информацию о голосах
    voice_count = synth.get_active_voice_count()
    print(f"\nАктивных голосов: {voice_count}")
    
    # Проверяем доступные программы
    programs = synth.get_available_programs()
    print(f"Доступно программ: {len(programs)}")
    if programs:
        print(f"Первые 5 программ: {programs[:5]}")
    
    print("Базовый тест завершен успешно!\n")


def test_advanced_features():
    """Тест расширенных возможностей"""
    print("=== Тест расширенных возможностей ===")
    
    synth = XGSynthesizer(sample_rate=48000, block_size=1024, max_polyphony=64)
    
    # Тест настройки параметров
    print("Настройка параметров...")
    synth.set_max_polyphony(128)
    synth.set_master_volume(0.8)
    print(f"Новая полифония: {synth.max_polyphony}")
    print(f"Новая мастер-громкость: {synth.master_volume}")
    
    # Тест SYSEX сообщений
    print("\nОтправка SYSEX сообщений...")
    # XG System On сообщение
    xg_sys_on = [0xF0, 0x43, 0x10, 0x4C, 0x00, 0x00, 0x7E, 0x00, 0xF7]
    synth.send_sysex(xg_sys_on)
    
    # Тест RPN/NRPN
    print("\nОтправка RPN/NRPN сообщений...")
    synth.send_midi_message(0xB0, 101, 0)  # RPN MSB
    synth.send_midi_message(0xB0, 100, 0)  # RPN LSB
    synth.send_midi_message(0xB0, 6, 2)    # Data Entry MSB (Pitch Bend Range = 2)
    
    # Тест Control Change
    print("\nОтправка Control Change сообщений...")
    synth.send_midi_message(0xB0, 1, 64)   # Modulation Wheel
    synth.send_midi_message(0xB0, 7, 100) # Volume
    synth.send_midi_message(0xB0, 10, 32) # Pan
    synth.send_midi_message(0xB0, 11, 127) # Expression
    synth.send_midi_message(0xB0, 64, 127) # Sustain Pedal On
    synth.send_midi_message(0xB0, 64, 0)   # Sustain Pedal Off
    
    # Тест Pitch Bend
    print("\nОтправка Pitch Bend сообщений...")
    synth.send_midi_message(0xE0, 0, 64)   # Pitch Bend Center
    synth.send_midi_message(0xE0, 127, 127) # Pitch Bend Max
    
    # Тест Program Change
    print("\nОтправка Program Change сообщений...")
    synth.send_midi_message(0xC0, 0)  # Program 0
    synth.send_midi_message(0xC0, 24) # Program 24
    
    # Тест Channel Pressure
    print("\nОтправка Channel Pressure сообщений...")
    synth.send_midi_message(0xD0, 64) # Channel Aftertouch
    
    # Тест Poly Pressure
    print("\nОтправка Poly Pressure сообщений...")
    synth.send_midi_message(0xA0, 60, 64) # Key Aftertouch для ноты C4
    
    print("Расширенный тест завершен успешно!\n")


def test_performance():
    """Тест производительности"""
    print("=== Тест производительности ===")
    
    synth = XGSynthesizer(sample_rate=44100, block_size=512, max_polyphony=64)
    
    # Создаем последовательность нот для теста
    notes = [(60 + i, 80 + i*2) for i in range(20)]  # 20 нот с разной скоростью
    
    print("Генерация последовательности нот...")
    
    # Отправляем ноты
    start_time = time.time()
    for note, velocity in notes:
        synth.send_midi_message(0x90, note, velocity)  # Note On
        synth.send_midi_message(0x80, note, 64)         # Note Off через короткое время
    
    # Генерируем аудио блоки
    block_sizes = [256, 512, 1024, 2048]
    for block_size in block_sizes:
        print(f"\nТест генерации блоков размером {block_size} сэмплов...")
        
        # Генерируем несколько блоков
        blocks_to_generate = 100
        gen_start = time.time()
        
        for _ in range(blocks_to_generate):
            left, right = synth.generate_audio_block(block_size)
        
        gen_end = time.time()
        total_time = gen_end - gen_start
        samples_generated = block_size * blocks_to_generate
        sample_rate_equivalent = samples_generated / total_time if total_time > 0 else 0
        
        print(f"  Сгенерировано: {samples_generated:,} сэмплов")
        print(f"  Время: {total_time:.4f} секунд")
        print(f"  Эквивалент частоты дискретизации: {sample_rate_equivalent/1000:.2f} кГц")
    
    end_time = time.time()
    print(f"\nОбщее время теста: {end_time - start_time:.4f} секунд")
    print("Тест производительности завершен!\n")


def test_error_handling():
    """Тест обработки ошибок"""
    print("=== Тест обработки ошибок ===")
    
    synth = XGSynthesizer()
    
    # Тест некорректных MIDI сообщений
    print("Тест некорректных MIDI сообщений...")
    try:
        synth.send_midi_message(0xFF, 0, 0)  # Некорректный статус
        print("  Некорректный статус обработан")
    except Exception as e:
        print(f"  Ошибка: {e}")
    
    # Тест некорректных SYSEX сообщений
    print("\nТест некорректных SYSEX сообщений...")
    try:
        synth.send_sysex([0xF0, 0xF7])  # Слишком короткое сообщение
        print("  Короткое SYSEX сообщение обработано")
    except Exception as e:
        print(f"  Ошибка: {e}")
    
    try:
        synth.send_sysex([0x90, 0x60, 0x7F])  # Не SYSEX сообщение
        print("  Не SYSEX сообщение обработано")
    except Exception as e:
        print(f"  Ошибка: {e}")
    
    # Тест генерации аудио с некорректными параметрами
    print("\nТест генерации аудио...")
    try:
        left, right = synth.generate_audio_block(0)  # Нулевой размер блока
        print(f"  Генерация с нулевым размером: {len(left)} сэмплов")
    except Exception as e:
        print(f"  Ошибка: {e}")
    
    # Тест сброса
    print("\nТест сброса синтезатора...")
    try:
        synth.reset()
        print("  Сброс выполнен успешно")
    except Exception as e:
        print(f"  Ошибка при сбросе: {e}")
    
    print("Тест обработки ошибок завершен!\n")


def main():
    """Основная функция тестирования"""
    print("Тестирование XG синтезатора")
    print("=" * 50)
    
    try:
        # Запускаем все тесты
        test_basic_functionality()
        test_advanced_features()
        test_performance()
        test_error_handling()
        
        print("Все тесты завершены успешно!")
        
    except Exception as e:
        print(f"Ошибка во время тестирования: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()