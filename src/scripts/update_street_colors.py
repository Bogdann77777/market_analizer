"""
CLI скрипт для обновления анализа улиц и цветов зон
Использование: python update_street_colors.py
"""

import sys
import os
from datetime import datetime

# Добавляем родительскую директорию в path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from analyzers.street_analyzer import analyze_all_streets


def main():
    """
    Главная функция CLI скрипта обновления анализа улиц
    """
    print("=" * 60)
    print("  ASHEVILLE LAND ANALYZER - STREET COLOR UPDATE")
    print("=" * 60)
    print()
    print(f"Запущено: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()

    # Запустить анализ всех улиц
    try:
        results = analyze_all_streets()

        # Подсчитать статистику по цветам
        if results:
            color_counts = {
                'green': 0,
                'light_green': 0,
                'yellow': 0,
                'red': 0
            }

            for analysis in results:
                color_counts[analysis.color] += 1

            total = len(results)

            print("\n" + "=" * 60)
            print("✅ АНАЛИЗ ЗАВЕРШЕН УСПЕШНО!")
            print()
            print(f"Обработано улиц: {total}")
            print()
            print("РАСПРЕДЕЛЕНИЕ ПО ЦВЕТАМ:")
            print(f"  🟢 Green ($350+):       {color_counts['green']:3d} ({color_counts['green']*100//total if total else 0}%)")
            print(f"  🟢 Light Green ($300-350): {color_counts['light_green']:3d} ({color_counts['light_green']*100//total if total else 0}%)")
            print(f"  🟡 Yellow ($220-300):   {color_counts['yellow']:3d} ({color_counts['yellow']*100//total if total else 0}%)")
            print(f"  🔴 Red (<$220):         {color_counts['red']:3d} ({color_counts['red']*100//total if total else 0}%)")
            print()
            print("Следующий шаг:")
            print("  - Запустите анализ рынка: python analyze_market_heat.py")
            print("  - Или сгенерируйте карту: python generate_map.py")
            print("=" * 60)
        else:
            print("\n" + "=" * 60)
            print("⚠️  АНАЛИЗ ЗАВЕРШЕН")
            print("   Нет данных для обработки (возможно пустая база)")
            print("=" * 60)

        sys.exit(0)

    except Exception as e:
        print("\n" + "=" * 60)
        print(f"❌ ОШИБКА АНАЛИЗА: {e}")
        print("=" * 60)
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
