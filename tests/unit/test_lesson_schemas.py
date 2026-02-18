"""Unit tests for lesson Pydantic schemas."""

import pytest


def test_lesson_summary_has_required_fields():
    """LessonSummary should have lesson_number, title, objective."""
    from app.schemas.lesson import LessonSummary

    summary = LessonSummary(
        lesson_number=5,
        title="Hobbies and Interests",
        objective="Learn to talk about hobbies"
    )
    assert summary.lesson_number == 5
    assert summary.title == "Hobbies and Interests"
    assert summary.objective == "Learn to talk about hobbies"


def test_lesson_summary_objective_optional():
    """LessonSummary objective should be optional."""
    from app.schemas.lesson import LessonSummary

    summary = LessonSummary(lesson_number=1, title="Introduction")
    assert summary.lesson_number == 1
    assert summary.objective is None


def test_vocabulary_item_schema():
    """VocabularyItemSchema should have english, spanish, category."""
    from app.schemas.lesson import VocabularyItemSchema

    item = VocabularyItemSchema(
        english="exercise",
        spanish="hacer ejercicio",
        category="verb"
    )
    assert item.english == "exercise"
    assert item.spanish == "hacer ejercicio"
    assert item.category == "verb"


def test_vocabulary_item_category_optional():
    """VocabularyItemSchema category should be optional."""
    from app.schemas.lesson import VocabularyItemSchema

    item = VocabularyItemSchema(english="hello", spanish="hola")
    assert item.category is None


def test_qa_pattern_schema():
    """QAPatternSchema should have pattern_number, templates, examples."""
    from app.schemas.lesson import QAPatternSchema

    pattern = QAPatternSchema(
        pattern_number=1,
        question_template="What do you like to do?",
        answer_template="I like to (*verb*).",
        examples=[{"q": "Why do you like to sing?", "a": "Because it's fun."}]
    )
    assert pattern.pattern_number == 1
    assert pattern.question_template == "What do you like to do?"
    assert len(pattern.examples) == 1


def test_lesson_detail_has_all_sections():
    """LessonDetail should include vocabulary, patterns, criteria."""
    from app.schemas.lesson import LessonDetail, VocabularyItemSchema, QAPatternSchema, EvaluationCriterionSchema

    detail = LessonDetail(
        lesson_number=5,
        title="Hobbies",
        objective="Learn hobbies",
        learning_principle_title="Faith",
        learning_principle_content="Learn by faith",
        vocabulary=[
            VocabularyItemSchema(english="fun", spanish="divertido", category="adjective")
        ],
        patterns=[
            QAPatternSchema(
                pattern_number=1,
                question_template="Q?",
                answer_template="A.",
                examples=[]
            )
        ],
        evaluation_criteria=[
            EvaluationCriterionSchema(criterion="Say why I like something")
        ]
    )
    assert detail.lesson_number == 5
    assert len(detail.vocabulary) == 1
    assert len(detail.patterns) == 1
    assert len(detail.evaluation_criteria) == 1
