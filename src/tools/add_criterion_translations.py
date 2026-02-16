#!/usr/bin/env python3
"""Add Spanish translations to evaluation criteria in markdown files.

Usage:
    python src/tools/add_criterion_translations.py                  # EC1 (default)
    python src/tools/add_criterion_translations.py --course ec2     # EC2
    python src/tools/add_criterion_translations.py --course all     # Both courses
"""

import argparse
import re
from pathlib import Path

# Course-specific lesson directories
COURSE_LESSONS_DIRS = {
    "ec1": Path(__file__).parent.parent.parent / "content/refined/ec1/books/englishconnect_1_para_los_alumnos/lessons",
    "ec2": Path(__file__).parent.parent.parent / "content/refined/ec2/books/englishconnect_2_for_learners/lessons",
}

# EC1 translations
EC1_TRANSLATIONS = {
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

# EC2 translations
EC2_TRANSLATIONS = {
    # Lesson 1
    "Ask for others' names.": "Preguntar los nombres de otros.",
    "Introduce myself and others.": "Presentarme a mí mismo y a otros.",
    "Understand how EnglishConnect can help me learn English.": "Entender cómo EnglishConnect puede ayudarme a aprender inglés.",

    # Lesson 2
    "Ask where others are from.": "Preguntar de dónde son otros.",
    "Say where I and others are from.": "Decir de dónde soy yo y de dónde son otros.",
    "Ask others what they like and don't like to do.": "Preguntar a otros qué les gusta y qué no les gusta hacer.",
    "Talk about what I and others like and don't like to do.": "Hablar sobre lo que a mí y a otros nos gusta y no nos gusta hacer.",

    # Lesson 3
    "Talk about what I like and don't like doing and why.": "Hablar sobre lo que me gusta y no me gusta hacer y por qué.",
    "Talk about what others like and don't like doing and why.": "Hablar sobre lo que a otros les gusta y no les gusta hacer y por qué.",

    # Lesson 4
    "Ask about others' extended families.": "Preguntar sobre las familias extendidas de otros.",
    "Talk about my and others' extended families.": "Hablar sobre mi familia extendida y la de otros.",

    # Lesson 5
    "Compare myself to others.": "Compararme con otros.",
    "Compare other people to each other.": "Comparar a otras personas entre sí.",

    # Lesson 6
    "Ask how others feel and why.": "Preguntar cómo se sienten otros y por qué.",
    "Talk about how I and others feel and why.": "Hablar sobre cómo me siento yo y cómo se sienten otros y por qué.",

    # Lesson 7
    "Ask for help.": "Pedir ayuda.",
    "Make requests.": "Hacer peticiones.",
    "Understand and respond to requests for help.": "Entender y responder a peticiones de ayuda.",

    # Lesson 8
    "Ask where others live.": "Preguntar dónde viven otros.",
    "Talk about where I and others live.": "Hablar sobre dónde vivo yo y dónde viven otros.",
    "Ask why others like or don't like living somewhere.": "Preguntar por qué a otros les gusta o no les gusta vivir en algún lugar.",
    "Talk about why I and others like or don't like living somewhere.": "Hablar sobre por qué a mí y a otros nos gusta o no nos gusta vivir en algún lugar.",

    # Lesson 9
    "Ask what others were like in the past.": "Preguntar cómo eran otros en el pasado.",
    "Talk about what I and others were like in the past.": "Hablar sobre cómo era yo y cómo eran otros en el pasado.",
    "Ask what others had in the past.": "Preguntar qué tenían otros en el pasado.",
    "Talk about what I and others had in the past.": "Hablar sobre lo que yo y otros teníamos en el pasado.",

    # Lesson 10
    "Ask about others' routines.": "Preguntar sobre las rutinas de otros.",
    "Talk about my and others' routines.": "Hablar sobre mi rutina y la de otros.",

    # Lesson 11
    "Ask what others did in the past.": "Preguntar qué hicieron otros en el pasado.",
    "Talk about what I and others did in the past.": "Hablar sobre lo que yo y otros hicimos en el pasado.",

    # Lesson 12
    "Ask where others were and why they did things in the past.": "Preguntar dónde estaban otros y por qué hicieron cosas en el pasado.",
    "Talk about where I and others were and why we did things in the past.": "Hablar sobre dónde estaba yo y otros y por qué hicimos cosas en el pasado.",

    # Lesson 13
    "Talk about my past experiences.": "Hablar sobre mis experiencias pasadas.",
    "Ask and answer questions about others' past experiences.": "Preguntar y responder sobre las experiencias pasadas de otros.",

    # Lesson 14
    "Talk about shopping for food.": "Hablar sobre las compras de comida.",
    "Ask how much something costs.": "Preguntar cuánto cuesta algo.",
    "Say how much something costs.": "Decir cuánto cuesta algo.",

    # Lesson 15
    "Ask about items.": "Preguntar sobre artículos.",
    "Talk about and compare items.": "Hablar sobre artículos y compararlos.",

    # Lesson 16
    "Ask about different locations.": "Preguntar sobre diferentes lugares.",
    "Talk about where places are.": "Hablar sobre dónde están los lugares.",

    # Lesson 17
    "Ask about future events.": "Preguntar sobre eventos futuros.",
    "Talk about future events.": "Hablar sobre eventos futuros.",
    "Make invitations.": "Hacer invitaciones.",

    # Lesson 18
    "Talk about what I and others usually do on holidays.": "Hablar sobre lo que yo y otros solemos hacer en los días festivos.",
    "Talk about what I and others plan to do on a holiday.": "Hablar sobre lo que yo y otros planeamos hacer en un día festivo.",

    # Lesson 19
    "Ask about others' vacations.": "Preguntar sobre las vacaciones de otros.",
    "Talk about what I will do on vacation.": "Hablar sobre lo que haré en vacaciones.",

    # Lesson 20
    "Ask how others are feeling.": "Preguntar cómo se sienten otros.",
    "Talk about how I and others are feeling.": "Hablar sobre cómo me siento yo y cómo se sienten otros.",
    "Ask for health advice.": "Pedir consejos de salud.",
    "Give health advice.": "Dar consejos de salud.",

    # Lesson 21
    "Ask about others' injuries.": "Preguntar sobre las lesiones de otros.",
    "Talk about my and others' injuries.": "Hablar sobre mis lesiones y las de otros.",

    # Lesson 22
    "Talk about future celebrations.": "Hablar sobre celebraciones futuras.",
    "Answer questions about future celebrations.": "Responder preguntas sobre celebraciones futuras.",
    "Invite others to future celebrations.": "Invitar a otros a celebraciones futuras.",

    # Lesson 23
    "Ask about past events.": "Preguntar sobre eventos pasados.",
    "Talk about past events.": "Hablar sobre eventos pasados.",

    # Lesson 24
    "Ask about others' goals and plans for the future.": "Preguntar sobre las metas y planes de otros para el futuro.",
    "Talk about my goals and plans for the future.": "Hablar sobre mis metas y planes para el futuro.",

    # Unit conclusions
    "Express my feelings and emotions.": "Expresar mis sentimientos y emociones.",
    "Describe where I live.": "Describir dónde vivo.",
    "Talk about my past.": "Hablar sobre mi pasado.",
    "Ask about personal information.": "Preguntar sobre información personal.",
    "Describe my hobbies and interests.": "Describir mis pasatiempos e intereses.",
    "Talk about family and friends.": "Hablar sobre la familia y los amigos.",
    "Describe my routines.": "Describir mis rutinas.",
    "Describe past experiences.": "Describir experiencias pasadas.",
    "Describe things for sale.": "Describir cosas en venta.",
    "Give directions.": "Dar direcciones.",
    "Describe future events.": "Describir eventos futuros.",
    "Describe holiday traditions.": "Describir tradiciones de días festivos.",
    "Describe how I feel.": "Describir cómo me siento.",
    "Describe past events.": "Describir eventos pasados.",
    "Describe my future goals.": "Describir mis metas futuras.",
}

# Merged dict for backwards compatibility
TRANSLATIONS = {**EC1_TRANSLATIONS, **EC2_TRANSLATIONS}


def add_translations_to_file(filepath: Path, translations: dict) -> int:
    """Add Spanish translations to evaluation criteria in a markdown file.

    Returns the number of translations added.
    """
    content = filepath.read_text(encoding='utf-8')
    original_content = content
    translations_added = 0

    # Process each known criterion
    for english, spanish in translations.items():
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
    parser = argparse.ArgumentParser(
        description="Add Spanish translations to evaluation criteria"
    )
    parser.add_argument(
        "--course",
        choices=["ec1", "ec2", "all"],
        default="ec1",
        help="Course to process (default: ec1)",
    )
    args = parser.parse_args()

    courses = ["ec1", "ec2"] if args.course == "all" else [args.course]

    for course in courses:
        lessons_dir = COURSE_LESSONS_DIRS[course]
        translations = EC1_TRANSLATIONS if course == "ec1" else EC2_TRANSLATIONS

        if not lessons_dir.exists():
            print(f"Error: Lessons directory not found: {lessons_dir}")
            continue

        print(f"\n=== {course.upper()} ===")
        total_translations = 0
        files_modified = 0

        for lesson_file in sorted(lessons_dir.glob("*.md")):
            count = add_translations_to_file(lesson_file, translations)
            if count > 0:
                print(f"{lesson_file.name}: Added {count} translations")
                total_translations += count
                files_modified += 1

        print(f"Total: Added {total_translations} translations to {files_modified} files")


if __name__ == "__main__":
    main()
