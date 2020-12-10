import json

from quizz import (
    Finish,
    Help,
    Jump,
    MultipleChoiceQuestion,
    Next,
    Previous,
    Quit,
    Quiz,
    Scheme,
)

warning = (
    "****" * 20
    + "\nWARNING: This questionnaire's purpose is to show capabilities of"
    " this library.\nIf you don't feel right, please consult to professional"
    " advice.\n" + "****" * 20
)


levels = {
    range(0, 11): "These ups and downs are considered normal",
    range(11, 17): "Mild mood disturbance",
    range(17, 21): "Borderline clinical depression",
    range(21, 31): "Moderate depression",
    range(31, 41): "Severe depression",
    range(41, 64): "Extreme depression",
}


with open("data.json") as file:
    question_data = json.loads(file.read())

    quiz = Quiz(
        questions=[
            MultipleChoiceQuestion("Choose one", choices=choices)
            for choices in question_data
        ],
        scheme=Scheme(
            style="number_fromzero",
            display="vertical",
            commands=[Next, Previous, Jump, Finish, Quit, Help],
        ),
    )

    print(warning)

    quiz.start()

    result = sum(int(question.answer.value) for question in quiz.questions)
    correspond = next(
        description
        for (scale, description) in levels.items()
        if result in scale
    )

    print(
        "Your answers added up to %d, which corresponds to: '%s'."
        % (result, correspond)
    )
    print(warning)
