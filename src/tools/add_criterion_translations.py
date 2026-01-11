#!/usr/bin/env python3
"""Add Spanish translations to evaluation criteria in markdown files.

Usage:
    python src/tools/add_criterion_translations.py
"""

import re
from pathlib import Path

# Define translations for each criterion
TRANSLATIONS = {
    # Lesson 1
    "Say my name and others' names.": "Decir mi nombre y los nombres de otros.",
    "Say hello and goodbye.": "Decir hola y adiós.",
    "Understand how EnglishConnect can help me learn English.": "Entender cómo EnglishConnect puede ayudarme a aprender inglés.",

    # Lesson 2
    "Greet someone and ask how they are.": "Saludar a alguien y preguntar cómo está.",
    "Introduce myself and say where I'm from.": "Presentarme y decir de dónde soy.",
    "Ask people's names and where they are from.": "Preguntar los nombres de las personas y de dónde son.",

    # Lesson 3
    "Say my birthday and anniversary.": "Decir mi cumpleaños y aniversario.",
    "Ask for and say someone's birthday and anniversary.": "Preguntar y decir el cumpleaños y aniversario de alguien.",

    # Lesson 4
    "Say what I like to do.": "Decir qué me gusta hacer.",
    "Say what I don't like to do.": "Decir qué no me gusta hacer.",
    "Ask what someone likes to do.": "Preguntar qué le gusta hacer a alguien.",

    # Lesson 5
    "Say why I like something.": "Decir por qué me gusta algo.",
    "Say why I don't like something.": "Decir por qué no me gusta algo.",

    # Lesson 6
    "Use family words.": "Usar palabras de familia.",
    "Say how many people are in my family.": "Decir cuántas personas hay en mi familia.",

    # Lesson 7
    "Describe myself and my family.": "Describirme a mí mismo y a mi familia.",
    "Ask about someone's family.": "Preguntar sobre la familia de alguien.",
    "Describe someone's family.": "Describir la familia de alguien.",

    # Lesson 8
    "Say what something is.": "Decir qué es algo.",
    "Use *this*, *that*, *these*, and *those*.": "Usar *this*, *that*, *these* y *those*.",
    "Ask if something belongs to someone.": "Preguntar si algo le pertenece a alguien.",

    # Lesson 9
    "Talk about clothing and colors.": "Hablar sobre ropa y colores.",
    "Say what I and others are wearing.": "Decir qué llevo puesto yo y otros.",

    # Lesson 10
    "Say what I do in my daily routine.": "Decir qué hago en mi rutina diaria.",
    "Say what someone does in their routine.": "Decir qué hace alguien en su rutina.",
    "Ask what someone does in their routine.": "Preguntar qué hace alguien en su rutina.",

    # Lesson 11
    "Say what I am doing now.": "Decir qué estoy haciendo ahora.",
    "Talk about what others are doing now.": "Hablar sobre qué están haciendo otros ahora.",
    "Describe daily routines.": "Describir rutinas diarias.",

    # Lesson 12
    "Say the time and date.": "Decir la hora y la fecha.",
    "Ask for the time and date.": "Preguntar la hora y la fecha.",

    # Lesson 13
    "Describe the weather.": "Describir el clima.",
    "Make predictions about the weather.": "Hacer predicciones sobre el clima.",

    # Lesson 14
    "Say where I work.": "Decir dónde trabajo.",
    "Say what my job is.": "Decir cuál es mi trabajo.",
    "Ask and say where someone works.": "Preguntar y decir dónde trabaja alguien.",
    "Ask and say what someone's job is.": "Preguntar y decir cuál es el trabajo de alguien.",

    # Lesson 15
    "Describe my job.": "Describir mi trabajo.",
    "Ask about someone's job.": "Preguntar sobre el trabajo de alguien.",
    "Describe other people's jobs.": "Describir los trabajos de otras personas.",

    # Lesson 16
    "Name foods for breakfast, lunch, and dinner.": "Nombrar comidas para el desayuno, almuerzo y cena.",
    "Talk about why I like or dislike certain foods.": "Hablar sobre por qué me gustan o no me gustan ciertas comidas.",
    "Ask why others like or dislike certain foods.": "Preguntar por qué a otros les gustan o no les gustan ciertas comidas.",

    # Lesson 17
    "Order food.": "Ordenar comida.",
    "Take someone's order.": "Tomar el pedido de alguien.",
    "Say what I want in, on, or with my food.": "Decir qué quiero en, sobre o con mi comida.",

    # Lesson 18
    "Say what ingredients are in foods.": "Decir qué ingredientes tienen las comidas.",
    "Describe how to make foods I like.": "Describir cómo hacer comidas que me gustan.",
    "Ask others how to make foods they like.": "Preguntar a otros cómo hacer comidas que les gustan.",

    # Lesson 19
    "Ask and answer questions about how much something costs.": "Preguntar y responder sobre cuánto cuesta algo.",
    "Say why I want to buy something.": "Decir por qué quiero comprar algo.",
    "Say why I don't want to buy something.": "Decir por qué no quiero comprar algo.",

    # Lesson 20
    "Talk about where I live.": "Hablar sobre dónde vivo.",
    "Ask and talk about where others live.": "Preguntar y hablar sobre dónde viven otros.",
    "Say where rooms are in a house or an apartment.": "Decir dónde están las habitaciones en una casa o apartamento.",

    # Lesson 21
    "Describe a bedroom and a bathroom.": "Describir una habitación y un baño.",
    "Describe where things are in a bedroom and a bathroom.": "Describir dónde están las cosas en una habitación y un baño.",

    # Lesson 22
    "Describe the location of places I visit.": "Describir la ubicación de lugares que visito.",
    "Ask for and give directions.": "Pedir y dar direcciones.",

    # Lesson 23
    "Name parts of my body.": "Nombrar partes de mi cuerpo.",
    "Say what part of my body hurts.": "Decir qué parte de mi cuerpo me duele.",
    "Say why my body hurts.": "Decir por qué me duele el cuerpo.",

    # Lesson 24
    "Describe how I feel when sick.": "Describir cómo me siento cuando estoy enfermo.",
    "Describe how others feel when sick.": "Describir cómo se sienten otros cuando están enfermos.",

    # Unit conclusions
    "Introduce myself and others.": "Presentarme a mí mismo y a otros.",
    "Ask about personal information.": "Preguntar sobre información personal.",
    "Describe my hobbies and interests.": "Describir mis pasatiempos e intereses.",
    "Identify common items.": "Identificar objetos comunes.",
    "Express likes and dislikes.": "Expresar gustos y disgustos.",
    "Describe my daily routine.": "Describir mi rutina diaria.",
    "Describe what I am doing.": "Describir qué estoy haciendo.",
    "Use days and times to talk about my day.": "Usar días y horas para hablar de mi día.",
    "Talk about my job.": "Hablar sobre mi trabajo.",
    "Describe foods I like and dislike.": "Describir comidas que me gustan y no me gustan.",
    "Explain why I like or dislike foods.": "Explicar por qué me gustan o no me gustan las comidas.",
    "Order food and take someone's order.": "Ordenar comida y tomar el pedido de alguien.",
    "Apply principles of learning by study and by faith.": "Aplicar principios de aprendizaje mediante el estudio y la fe.",
    "Explain how to make different foods.": "Explicar cómo hacer diferentes comidas.",
    "Talk about buying or selling something.": "Hablar sobre comprar o vender algo.",
    "Describe where I live.": "Describir dónde vivo.",
    "Describe how I feel.": "Describir cómo me siento.",
    "Talk about illnesses.": "Hablar sobre enfermedades.",
}


def add_translations_to_file(filepath: Path) -> int:
    """Add Spanish translations to evaluation criteria in a markdown file.

    Returns the number of translations added.
    """
    content = filepath.read_text(encoding='utf-8')
    original_content = content
    translations_added = 0

    # Process each known criterion
    for english, spanish in TRANSLATIONS.items():
        # Pattern: • English criterion (not already followed by _es translation)
        # We need to check if the translation already exists
        pattern = rf'(• {re.escape(english)})\n(?!• _es:)'
        replacement = rf'\1\n• _es: {spanish}\n'

        new_content = re.sub(pattern, replacement, content)
        if new_content != content:
            translations_added += 1
            content = new_content

    if content != original_content:
        filepath.write_text(content, encoding='utf-8')
        return translations_added

    return 0


def main():
    """Add translations to all lesson files."""
    lessons_dir = Path("content/refined/ec1/books/englishconnect_1_para_los_alumnos/lessons")

    if not lessons_dir.exists():
        print(f"Error: Lessons directory not found: {lessons_dir}")
        return

    total_translations = 0
    files_modified = 0

    for lesson_file in sorted(lessons_dir.glob("*.md")):
        count = add_translations_to_file(lesson_file)
        if count > 0:
            print(f"{lesson_file.name}: Added {count} translations")
            total_translations += count
            files_modified += 1

    print(f"\nTotal: Added {total_translations} translations to {files_modified} files")


if __name__ == "__main__":
    main()
