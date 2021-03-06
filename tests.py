import itertools
import re

from unittest import TestCase
from unittest.mock import ANY, call, patch

from quizz import (
    AlphaNumericValidator,
    AlphaValidator,
    Answers,
    Command,
    DigitValidator,
    Finish,
    Help,
    Jump,
    MaxLengthValidator,
    MinLengthValidator,
    MultipleChoiceQuestion,
    Next,
    Option,
    Previous,
    Question,
    Quit,
    Quiz,
    RegexValidator,
    Scheme,
    Skip,
    ValidationError,
    Validator,
    opcodes,
)


class TestQuestion(TestCase):
    def test_eq(self):
        a, b, c = Question("?"), Question("?"), 5
        self.assertFalse(a == b)
        self.assertFalse(b == c)  # NotImplemented

    def test_str(self):
        question = Question("What?")
        self.assertEqual("<Question: What?>", str(question))

    def test_empty_prompt_raises_error(self):
        with self.assertRaisesRegex(
            ValueError, "A question should at least define a prompt."
        ):
            Question("")

    def test_default_instance_attribute_values(self):
        question = Question("What?")

        self.assertEqual("What?", question.prompt)
        self.assertIsNone(question.answer)
        self.assertIsNone(question.quiz)
        self.assertEqual(0, question.sequence)
        self.assertEqual(0, question.attempt)

        self.assertEqual([], question.validators)
        self.assertEqual([], question.options)
        self.assertEqual([], question.commands)
        self.assertEqual([], question.correct_answers)
        self.assertEqual({}, question.extra)

        self.assertTrue(question.required)
        self.assertTrue(question.strip)

        self.assertEqual("", question.suffix)
        self.assertEqual("", question.prefix)

        self.assertEqual("!", question.command_delimiter)
        self.assertEqual(") ", question.option_indicator)

        self.assertIsNone(question.scheme)

    @patch("quizz.stdin", return_value="x")
    def test_attempt_increments_on_ask(self, *_):
        question = Question("What?")
        question.ask()
        self.assertEqual(1, question.attempt)
        question.ask()
        self.assertEqual(2, question.attempt)

    @patch("quizz.stdin", return_value="Answer")
    def test_answer_is_set(self, *_):
        question = Question("What?")
        question.ask()
        self.assertEqual("Answer", question.answer)

    @patch("quizz.stdin", side_effect=[""])
    def test_answer_persists_on_empty_input(self, *_):
        question = Question("What?", required=False)
        question.answer = "Previous Answer"
        question.ask()

        self.assertEqual("Previous Answer", question.answer)

    @patch("quizz.stdin", return_value="A")
    def test_answer_is_set_as_option(self, *_):
        option = Option(value="A", expression="Hello")
        question = Question("What?", options=[option])

        question.ask()
        self.assertEqual(option, question.answer)

    @patch("quizz.stdin", side_effect=["", "OK", "Not OK"])
    @patch("quizz.stdout")
    def test_required_retries(self, mock_stdout, *_):
        question = Question("What?")
        self.assertTrue(question.get_required())

        question.ask()

        mock_stdout.assert_called_with("This question is required.")
        self.assertEqual("OK", question.answer)
        self.assertEqual(2, question.attempt)

    @patch("quizz.stdin", return_value=" spaced ")
    def test_strip(self, *_):
        question = Question("What?")
        self.assertTrue(question.get_strip())

        question_no_strip = Question("What? 2", strip=False)
        self.assertFalse(question_no_strip.get_strip())

        question.ask()
        question_no_strip.ask()

        self.assertEqual("spaced", question.answer)
        self.assertEqual(" spaced ", question_no_strip.answer)

    @patch("quizz.stdin", return_value="Answer")
    def test_suffix(self, mock_stdin):
        question = Question("What?")
        question_with_suffix = Question("What?", suffix="test")

        self.assertEqual("", question.get_suffix())
        self.assertEqual("test", question_with_suffix.get_suffix())

        self.assertEqual("What?", question.get_prompt())
        self.assertEqual("What?test", question_with_suffix.get_prompt())

        question.ask()
        mock_stdin.assert_called_with("What?")

        question_with_suffix.ask()
        mock_stdin.assert_called_with("What?test")

    @patch("quizz.stdin", return_value="Answer")
    def test_prefix(self, mock_stdin):
        question_with_prefix = Question("What?", prefix="test2")

        self.assertEqual("test2", question_with_prefix.get_prefix())
        self.assertEqual("test2What?", question_with_prefix.get_prompt())

        question_with_prefix.ask()
        mock_stdin.assert_called_with("test2What?")

    @patch("quizz.stdin", return_value="Answer")
    def test_prefix_suffix(self, mock_stdin):
        question_with_prefix_suffix = Question(
            "What?", prefix="Pre", suffix="Suf"
        )

        self.assertEqual("Pre", question_with_prefix_suffix.get_prefix())
        self.assertEqual("Suf", question_with_prefix_suffix.get_suffix())
        self.assertEqual(
            "PreWhat?Suf", question_with_prefix_suffix.get_prompt()
        )

        question_with_prefix_suffix.ask()
        mock_stdin.assert_called_with("PreWhat?Suf")

    @patch("quizz.stdin", side_effect=["Answer", ""])
    def test_has_answer(self, *_):
        question = Question("What?")
        question.ask()
        self.assertTrue(question.has_answer)

        optional_question = Question("What?", required=False)
        optional_question.ask()
        self.assertFalse(optional_question.has_answer)

    @patch("quizz.stdin", side_effect=["Correct", "Incorrect", ""])
    def test_has_correct_answer(self, *_):
        question = Question("What?", correct_answers=["Correct"])
        incorrect_question = Question(
            "What?", correct_answers=["Hello", "Girl"]
        )
        unanswered_question = Question("What", required=False)

        self.assertIn("Correct", question.get_correct_answers())
        self.assertIn("Girl", incorrect_question.get_correct_answers())
        self.assertIn("Hello", incorrect_question.get_correct_answers())

        question.ask()
        incorrect_question.ask()
        unanswered_question.ask()

        self.assertTrue(question.has_correct_answer)
        self.assertFalse(incorrect_question.has_correct_answer)
        self.assertFalse(unanswered_question.has_correct_answer)

    @patch("quizz.stdin", side_effect=["B", "A"])
    def test_has_correct_answer_option(self, *_):
        options = [
            Option(value="A", expression="Something"),
            Option(value="B", expression="Other Something"),
        ]
        question = Question("What?", options=options, correct_answers=["A"])

        question.ask()
        self.assertFalse(question.has_correct_answer)

        question.ask()
        self.assertTrue(question.has_correct_answer)

    @patch("quizz.stdin", side_effect=["invalid", "A"])
    @patch("quizz.stdout")
    def test_option_validation(self, mock_stdout, *_):
        question = Question(
            "What?",
            options=[
                Option(value="A", expression="Something"),
                Option(value="B", expression="Other Something"),
            ],
        )

        question.ask()

        mock_stdout.assert_called_with(
            "\nThe selected option is not valid. Available options are: "
            "\nA) Something\nB) Other Something\n"
        )

        self.assertEqual(2, question.attempt)

    @patch("quizz.stdin", side_effect=["Invalid1", "AnotherInvalid", "Valid"])
    @patch("quizz.stdout")
    def test_validation(self, mock_stdout, *_):
        question = Question(
            "What",
            validators=[
                AlphaValidator(message="This answer is not alpha."),
                MaxLengthValidator(13, message="This answer is too long."),
            ],
        )

        question.ask()

        mock_stdout.assert_has_calls(
            [
                call("This answer is not alpha."),
                call("This answer is too long."),
            ]
        )
        self.assertEqual(3, question.attempt)

    @patch("quizz.stdin", return_value="Answer")
    def test_signals(self, *_):
        question = Question("What?", extra={"number": 10})

        def increment_number(q):
            q.extra["number"] *= 8
            q.extra["ans"] = q.answer

        def decrement_number(q):
            q.extra["number"] -= 5
            q.extra["ans"] = q.answer

        question.pre_ask = increment_number
        question.post_answer = decrement_number

        question.ask()

        self.assertEqual(75, question.extra["number"])
        self.assertEqual(question.answer, question.extra["ans"])

    def test_update_scheme_no_force(self):
        my_scheme = Scheme(commands=[Jump])
        question = Question("What?", scheme=my_scheme)

        self.assertEqual([my_scheme], question.mounted_schemes)

        question.update_scheme(my_scheme)

        self.assertEqual([my_scheme], question.mounted_schemes)
        self.assertEqual([Jump], question.commands)

    def test_update_scheme_force(self):
        my_scheme = Scheme(commands=[Jump])
        question = Question("What?", scheme=my_scheme)

        self.assertEqual([my_scheme], question.mounted_schemes)

        question.update_scheme(my_scheme, force=True)

        self.assertEqual([my_scheme, my_scheme], question.mounted_schemes)
        self.assertEqual([Jump, Jump], question.commands)

    def test_empty_scheme_has_no_effect(self):
        from quizz import _field_names  # noqa

        empty = Scheme()
        question = Question("What?", scheme=empty)
        question_no_scheme = Question("What?")

        for name in _field_names:
            if hasattr(question_no_scheme, name):
                self.assertEqual(
                    getattr(question_no_scheme, name), getattr(question, name)
                )

    def test_scheme_skips_unknown_attribute(self):
        my_scheme = Scheme(display="foobar")
        question = Question("What?", scheme=my_scheme)

        self.assertFalse(hasattr(question, "display"))

    def test_scheme_does_not_skip_empty_strings(self):
        my_scheme = Scheme(prompt="", option_indicator="")
        question = Question("What?", scheme=my_scheme)

        self.assertEqual("", question.prompt)
        self.assertEqual("", question.option_indicator)

    def test_scheme_overrides_immutable(self):
        my_scheme = Scheme(
            prompt="Whats up?",
            required=False,
            strip=False,
            suffix="abc",
            prefix="def",
            command_delimiter="x",
            option_indicator="-",
        )

        question = Question("What?", scheme=my_scheme)

        self.assertEqual("Whats up?", question.prompt)
        self.assertEqual("x", question.command_delimiter)
        self.assertEqual("-", question.option_indicator)
        self.assertEqual("abc", question.suffix)
        self.assertEqual("def", question.prefix)

        self.assertFalse(question.required)
        self.assertFalse(question.strip)

    def test_scheme_extends_list(self):
        alpha, digit, max_len = (
            AlphaValidator(),
            DigitValidator(),
            MaxLengthValidator(10),
        )

        my_scheme = Scheme(
            validators=[alpha],
            correct_answers=["SchemeAnswer", "SchemeAnswer2"],
            commands=[Skip],
        )

        empty_question = Question("What?", scheme=my_scheme)
        self.assertEqual([alpha], empty_question.validators)
        self.assertEqual([Skip], empty_question.commands)
        self.assertEqual(
            ["SchemeAnswer", "SchemeAnswer2"], empty_question.correct_answers
        )

        question = Question(
            "What?",
            validators=[digit, max_len],
            correct_answers=["RealAnswer"],
            commands=[Skip],
            scheme=my_scheme,
        )
        self.assertEqual([digit, max_len, alpha], question.validators)
        self.assertEqual([Skip, Skip], question.commands)
        self.assertEqual(
            ["RealAnswer", "SchemeAnswer", "SchemeAnswer2"],
            question.correct_answers,
        )

    def test_scheme_extends_dict(self):
        my_scheme = Scheme(extra={"foo": "bar", "baz": "qux"})

        question = Question("What?", scheme=my_scheme)
        question_with_extra = Question(
            "What?", extra={"hello": 5}, scheme=my_scheme
        )

        self.assertEqual({"foo": "bar", "baz": "qux"}, question.extra)
        self.assertEqual(
            {"hello": 5, "foo": "bar", "baz": "qux"},
            question_with_extra.extra,
        )

    def test_scheme_dict_disallow_key_overriding(self):
        my_scheme = Scheme(extra={"foo": "bar"})
        question = Question("What?", extra={"foo": "baz"}, scheme=my_scheme)

        self.assertEqual({"foo": "baz"}, question.extra)

    def test_scheme_allows_external_interference(self):
        my_scheme = Scheme(prompt="Hello")
        question = Question("What?")

        question.update_scheme(my_scheme)
        self.assertEqual("Hello", question.prompt)

    @patch("quizz.stdin", side_effect=["!command", "Answer"])
    @patch("quizz.stdout")
    def test_command_no_context(self, mock_stdout, *_):
        question = Question("What?", required=False)
        question.ask()

        mock_stdout.assert_called_with(
            "Commands are disabled for this question."
        )
        self.assertEqual("Answer", question.answer)

    @patch("quizz.stdin", side_effect=["/hello", "/search test", "Answer"])
    @patch("quizz.stdout")
    def test_command_not_found(self, mock_stdout, *_):
        # Also tests: command delimiter & first word counts as expression
        question = Question("What?", command_delimiter="/", commands=[Help])
        question.ask()

        mock_stdout.assert_has_calls(
            [
                call("Command not found: hello"),
                call("Command not found: search"),
            ]
        )
        self.assertEqual("Answer", question.answer)

    @patch("quizz.stdin", side_effect=["    !hello", "Answer"])
    @patch("quizz.stdout")
    def test_command_strips(self, mock_stdout, *_):
        # Also tests: get_commands
        question = Question("What?", commands=[Help])
        question.ask()

        mock_stdout.assert_called_with("Command not found: hello")
        self.assertEqual([Help], question.get_commands())

    @patch("quizz.stdin", side_effect=["!meow", "!meow", "Cat!"])
    def test_command_opcode_continue(self, *_):
        class Meow(Command):
            expression = "meow"

            def execute(self, question, *args):
                question.extra["meow_count"] += 1
                return opcodes.CONTINUE

        meowing_question = Question(
            "What?", commands=[Meow], extra={"meow_count": 0}, required=False
        )
        meowing_question.ask()

        self.assertEqual("Cat!", meowing_question.answer)
        self.assertEqual(2, meowing_question.extra["meow_count"])
        self.assertEqual(3, meowing_question.attempt)

    @patch("quizz.stdin", side_effect=["!meow", "!meow", "Cat!"])
    def test_command_opcode_none(self, *_):
        # Returning None in opcode does not re-ask the question.
        # It will re-ask the question if it is required though.

        class Meow(Command):
            expression = "meow"

            def execute(self, question, *args):
                question.extra["meow_count"] += 1

        meowing_question = Question(
            "What?", commands=[Meow], extra={"meow_count": 0}, required=False
        )
        meowing_question.ask()

        self.assertIsNone(meowing_question.answer)
        self.assertEqual(1, meowing_question.extra["meow_count"])
        self.assertEqual(1, meowing_question.attempt)

    @patch("quizz.stdin", side_effect=["!meow", "!meow", "Cat!"])
    @patch("quizz.stdout")
    def test_command_opcode_none_required(self, mock_stdout, *_):
        # Re-ask the question if it is required even if opcode
        # is None. use BREAK to bypass required as well.

        class Meow(Command):
            expression = "meow"

            def execute(self, question, *args):
                question.extra["meow_count"] += 1

        meowing_question = Question(
            "What?", commands=[Meow], extra={"meow_count": 0}
        )
        meowing_question.ask()

        mock_stdout.assert_has_calls(
            [
                call("This question is required."),
                call("This question is required."),
            ]
        )
        self.assertEqual("Cat!", meowing_question.answer)
        self.assertEqual(2, meowing_question.extra["meow_count"])
        self.assertEqual(3, meowing_question.attempt)

    @patch("quizz.stdin", side_effect=["!break", "!meow", "Cat!"])
    def test_command_opcode_break(self, *_):
        # Required question is break-able
        class Break(Command):
            expression = "break"

            def execute(self, question, *args):
                return opcodes.BREAK

        question_ = Question("What?", commands=[Break])
        question_.ask()

        self.assertIsNone(question_.answer)
        self.assertEqual(1, question_.attempt)

    @patch("quizz.stdin", side_effect=["!set_extra cat meow", "Answer"])
    def test_command_with_args(self, *_):
        class SetExtra(Command):
            expression = "set_extra"

            def execute(self, question, *args):
                question.extra[args[0]] = args[1]
                return opcodes.CONTINUE

        question_ = Question("What?", commands=[SetExtra])
        question_.ask()

        self.assertEqual("meow", question_.extra["cat"])
        self.assertEqual("Answer", question_.answer)
        self.assertEqual(2, question_.attempt)


class TestMultipleChoiceQuestion(TestCase):
    def test_str(self):
        question = MultipleChoiceQuestion("What?", choices=["A"])
        self.assertEqual("<MultipleChoiceQuestion: What?>", str(question))

    def test_inherits_question(self):
        self.assertTrue(issubclass(MultipleChoiceQuestion, Question))

    def test_default_instance_attribute_values(self):
        question = MultipleChoiceQuestion(
            "What?", options=[Option(value="Hello", expression="World")]
        )

        self.assertEqual([], question.choices)
        self.assertEqual("horizontal", question.display)
        self.assertEqual("letter", question.style)
        self.assertIsNone(question.style_iterator)

    @patch("quizz.stdin", return_value="Answer")
    def test_no_options_provided(self, *_):
        with self.assertRaisesRegex(
            ValueError,
            "MultipleChoiceQuestion should"
            " at least have one member in 'options' or 'choices' attributes.",
        ):
            MultipleChoiceQuestion("What?")

    def test_choices_converted_to_options(self):
        choices = ["Hello", "World"]
        question = MultipleChoiceQuestion("What?", choices=choices)

        self.assertEqual(len(choices), len(question.options))

        for option, expression in zip(question.get_options(), choices):
            self.assertEqual(expression, option.expression)

    def test_choices_combined_with_options(self):
        question = MultipleChoiceQuestion(
            "What?",
            choices=["Hello", "World"],
            options=[Option(value="Hello", expression="World")],
        )

        self.assertEqual(
            [
                Option(value="a", expression="Hello"),
                Option(value="b", expression="World"),
                Option(value="Hello", expression="World"),
            ],
            question.get_options(),
        )

    def test_choices_combined_with_options_with_scheme(self):
        scheme = Scheme(options=[Option(value="Cat", expression="Meow")])

        question = MultipleChoiceQuestion(
            "What?",
            choices=["Hello", "World"],
            options=[Option(value="Hello", expression="World")],
            scheme=scheme,
        )

        self.assertEqual(
            [
                Option(value="a", expression="Hello"),
                Option(value="b", expression="World"),
                Option(value="Hello", expression="World"),
                Option(value="Cat", expression="Meow"),
            ],
            question.get_options(),
        )

        self.assertEqual(
            [
                Option(value="Hello", expression="World"),
                Option(value="Cat", expression="Meow"),
            ],
            question.primitive_options,
        )

        # External update
        new_scheme = Scheme(options=[Option(value="Dog", expression="Bark")])
        question.update_scheme(new_scheme)

        self.assertEqual(
            [
                Option(value="Hello", expression="World"),
                Option(value="Cat", expression="Meow"),
                Option(value="Dog", expression="Bark"),
            ],
            question.primitive_options,
        )

        self.assertEqual(
            [
                Option(value="a", expression="Hello"),
                Option(value="b", expression="World"),
                Option(value="Hello", expression="World"),
                Option(value="Cat", expression="Meow"),
                Option(value="Dog", expression="Bark"),
            ],
            question.get_options(),
        )

    def test_choices_update_options_with_scheme(self):
        scheme = Scheme(choices=["Cat", "Dog", "Fish"])
        question = MultipleChoiceQuestion(
            "What?", choices=["Chicken"], scheme=scheme
        )

        self.assertEqual(
            [
                Option(value="a", expression="Chicken"),
                Option(value="b", expression="Cat"),
                Option(value="c", expression="Dog"),
                Option(value="d", expression="Fish"),
            ],
            question.get_options(),
        )

        # External update
        new_scheme = Scheme(choices=["Cow"])
        question.update_scheme(new_scheme)

        self.assertEqual(
            [
                Option(value="a", expression="Chicken"),
                Option(value="b", expression="Cat"),
                Option(value="c", expression="Dog"),
                Option(value="d", expression="Fish"),
                Option(value="e", expression="Cow"),
            ],
            question.get_options(),
        )

        self.assertEqual([], question.primitive_options)

    def test_invalid_style_iterator(self):
        with self.assertRaisesRegex(
            ValueError,
            re.escape(
                "Unknown style or invalid style iterator. Built-in styles are:"
                " (letter, letter_uppercase, number, number_fromzero)"
            ),
        ):
            MultipleChoiceQuestion("What?", choices=["A"], style="?")

    def _test_style(self, style, sample):
        question = MultipleChoiceQuestion(
            "What?", style=style, choices=["???" for _ in range(len(sample))]
        )

        for option, value in zip(question.get_options(), sample):
            self.assertEqual(value, option.value)

    def test_styles(self):
        self._test_style("letter", ["a", "b", "c", "d", "e", "f"])
        self._test_style("letter_uppercase", ["A", "B", "C", "D", "E", "F"])
        self._test_style("number", ["1", "2", "3", "4", "5", "6"])
        self._test_style("number_fromzero", ["0", "1", "2", "3", "4", "5"])

    def _test_style_iterator(self, iterator, sample):
        question = MultipleChoiceQuestion(
            "What?",
            style_iterator=iterator,
            choices=["???" for _ in range(len(sample))],
        )

        for option, value in zip(question.get_options(), sample):
            self.assertEqual(value, option.value)

    def test_custom_style_iterators(self):
        self._test_style_iterator("Love", ["L", "o", "v", "e"])
        self._test_style_iterator(
            itertools.cycle("Love"),
            ["L", "o", "v", "e", "L", "o", "v"],
        )
        self._test_style_iterator(
            ["".join(comb) for comb in itertools.combinations("ABCD", 2)],
            ["AB", "AC", "AD", "BC", "BD", "CD"],
        )

    @patch("quizz.stdin", return_value="a")
    def test_display_none(self, mock_stdin):
        question = MultipleChoiceQuestion("What?", choices=["A"], display=None)
        question.ask()

        mock_stdin.assert_called_with("What?")
        self.assertIsNone(question.get_display())

    @patch("quizz.stdin", return_value="a")
    def test_display_horizontal(self, mock_stdin):
        question = MultipleChoiceQuestion(
            "What?", choices=["A", "B", "C", "D"], display="horizontal"
        )

        question.ask()
        mock_stdin.assert_called_with(
            "What?\na) A  b) B  c) C  d) D\nYour answer: "
        )

    @patch("quizz.stdin", return_value="a")
    def test_display_vertical(self, mock_stdin):
        question = MultipleChoiceQuestion(
            "What?",
            choices=["A", "B", "C", "D"],
            display="vertical",
            option_indicator="-)",
        )

        question.ask()
        mock_stdin.assert_called_with(
            "What?\na-)A\nb-)B\nc-)C\nd-)D\nYour answer: "
        )

    def test_display_invalid(self):
        question = MultipleChoiceQuestion(
            "What?", choices=["A"], display="Cat"
        )

        with self.assertRaisesRegex(
            NotImplementedError,
            re.escape(
                "There is no such display 'Cat'. Built-in displays are:"
                " (vertical, horizontal). You may create this display by"
                " implementing get_Cat_display method."
            ),
        ):
            question.get_prompt()

    def test_custom_display_implementation(self):
        class CustomQuestion(MultipleChoiceQuestion):
            def get_cat_display(self, prompt):  # noqa
                return "Meow"

        question = CustomQuestion("What?", choices=["A"], display="cat")
        self.assertEqual("Meow", question.get_prompt())


class TestQuiz(TestCase):
    def test_default_scheme_has_finish_command(self):
        question = Question("What?")
        Quiz(questions=[question])

        self.assertEqual([Finish], question.commands)

    def test_empty_scheme_removes_finish_command(self):
        question = Question("What?")
        Quiz(questions=[question], scheme=Scheme())

        self.assertEqual([], question.commands)

    @patch("quizz.Question.update_scheme")
    def test_update_scheme_gets_called(self, mock_update_scheme):
        my_scheme = Scheme(command_delimiter="**")
        Quiz(questions=[Question("What?")], scheme=my_scheme)

        mock_update_scheme.assert_called_with(my_scheme, force=False)

    def test_quiz_sets_question_sequence_and_self(self):
        question = Question("What?")
        question1 = MultipleChoiceQuestion("What?", choices=["A"])

        self.assertEqual(0, question.sequence)
        self.assertEqual(0, question1.sequence)
        self.assertIsNone(question.quiz)
        self.assertIsNone(question1.quiz)

        quiz = Quiz(questions=[question, question1])

        self.assertEqual(0, question.sequence)
        self.assertEqual(1, question1.sequence)
        self.assertEqual(quiz, question.quiz)
        self.assertEqual(quiz, question1.quiz)

    def test_update_manually(self):
        a, b = Question("A"), Question("B")

        quiz = Quiz(questions=[a])
        quiz.questions.append(b)

        self.assertIsNone(b.quiz)
        self.assertEqual([a, b], quiz.required_questions)
        self.assertEqual(0, b.sequence)

        b.quiz = quiz  # Manual assignment, instead of quiz.update()

        self.assertEqual(quiz, b.quiz)
        self.assertEqual(1, b.sequence)
        self.assertEqual([], b.mounted_schemes)

    def test_update(self):
        a, b = Question("a"), Question("b")

        quiz = Quiz(questions=[a])
        quiz.questions.append(b)

        self.assertIsNone(b.quiz)
        self.assertEqual([a, b], quiz.required_questions)
        self.assertEqual(0, b.sequence)

        quiz.update()

        self.assertEqual(quiz, b.quiz)
        self.assertEqual(1, b.sequence)

        # update() should add Quiz's scheme. (default scheme, in this case)
        self.assertEqual([Scheme(commands=[Finish])], b.mounted_schemes)

    def test_update_scheme_applies(self):
        my_scheme = Scheme(commands=[Skip])

        a, b = Question("a"), Question("b")
        quiz = Quiz(questions=[a], scheme=my_scheme)

        quiz.questions.append(b)
        quiz.update()

        self.assertEqual([my_scheme], b.mounted_schemes)

    def test_update_scheme_do_not_force(self):
        # Same scheme is not applied twice if force_scheme=False
        my_scheme = Scheme(commands=[Skip])

        a, b = Question("a"), Question("b", scheme=my_scheme)
        quiz = Quiz(questions=[a], scheme=my_scheme)

        quiz.questions.append(b)
        quiz.update()

        self.assertEqual([my_scheme], b.mounted_schemes)

    def test_update_scheme_force(self):
        my_scheme = Scheme(commands=[Skip])

        a, b = Question("a"), Question("b", scheme=my_scheme)
        quiz = Quiz(questions=[a], scheme=my_scheme)

        quiz.questions.append(b)
        quiz.update(force_scheme=True)

        self.assertEqual([my_scheme, my_scheme], b.mounted_schemes)

    def test_question_pre(self):
        question = Question("What?")
        Quiz(questions=[question])

        self.assertEqual(
            "* Question 1/1. [No answer]\n", question.get_question_pre()
        )

        question.answer = "Good answer"
        self.assertEqual(
            "* Question 1/1. [Good answer]\n", question.get_question_pre()
        )

        question.answer = Option(value="A", expression="Best answer.")
        self.assertEqual(
            "* Question 1/1. [A) Best answer.]\n", question.get_question_pre()
        )

    def test_question_prompt_changes_with_quiz(self):
        question = Question("What?")
        question2 = Question("Hello?")
        Quiz(questions=[question, question2])

        self.assertEqual(
            "* Question 1/2. [No answer]\nWhat?", question.get_prompt()
        )

        question.update_scheme(Scheme(suffix="Suf", prefix="Pre"))
        self.assertEqual(
            "* Question 1/2. [No answer]\nPreWhat?Suf", question.get_prompt()
        )

    @patch("quizz.stdin", side_effect=["", "What", "Hello", "!finish"])
    @patch("quizz.stdout")  # Silent output in test
    def test_quiz_inquiries_get_incremented(self, *_):
        questions = [Question("What?"), Question("Hello?")]
        quiz = Quiz(questions=questions)
        quiz.start()

        self.assertEqual(4, quiz.inquiries)
        self.assertEqual(sum(q.attempt for q in questions), quiz.inquiries)

    @patch("quizz.stdin", side_effect=["Yes", "No", "!finish"])
    @patch("quizz.stdout")
    def test_quiz_index_corresponds_question_sequence(self, *_):
        question = Question("What?")
        question1 = Question("Hello?")

        question.pre_ask = question1.pre_ask = lambda q: self.assertEqual(
            q.sequence, q.quiz.index
        )
        quiz = Quiz(questions=[question, question1])
        quiz.start()

    def test_required_questions_and_min_inquiries(self):
        q = Question("Hello?")
        q1 = Question("Hello?", required=False)
        q2 = Question("Hello?")
        q3 = Question("Hello?")
        q4 = Question("Hello?", required=False)

        quiz = Quiz(questions=[q, q1, q2, q3, q4])

        self.assertEqual([q, q2, q3], quiz.required_questions)
        self.assertEqual(3, quiz.min_inquiries)

    @patch("quizz.stdin", return_value="!finish")
    @patch("quizz.stdout")
    def test_start(self, *_):
        q = Question("Hello?", required=False)
        q1 = Question("Hello?", required=False)
        quiz = Quiz(questions=[q, q1])

        quiz.start()

        self.assertEqual(1, quiz.inquiries)
        self.assertEqual(1, q.attempt)
        self.assertEqual(0, q1.attempt)

    @patch("quizz.stdin", return_value="!finish")
    @patch("quizz.stdout")
    def test_start_arbitrary_index(self, *_):
        q = Question("Hello?", required=False)
        q1 = Question("Hello?", required=False)
        quiz = Quiz(questions=[q, q1])

        quiz.index = 1
        quiz.start()

        self.assertEqual(1, quiz.inquiries)
        self.assertEqual(0, q.attempt)
        self.assertEqual(1, q1.attempt)

    def test_done_ready_api(self):
        q1, q2, q3 = (
            Question("What?"),
            Question("What?", required=False),
            Question("What?"),
        )

        quiz = Quiz(questions=[q1, q2, q3])

        self.assertFalse(quiz.is_ready)
        self.assertFalse(quiz.is_done)

        q1.answer = q3.answer = "A"

        self.assertFalse(quiz.is_ready)
        self.assertFalse(quiz.is_done)

        quiz.inquiries = 2

        self.assertTrue(quiz.is_ready)
        self.assertFalse(quiz.is_done)

        q2.answer = "A"

        self.assertTrue(quiz.is_ready)
        self.assertTrue(quiz.is_done)

        q1.answer = None

        self.assertFalse(quiz.is_ready)
        self.assertFalse(quiz.is_done)

    @patch("quizz.stdin", side_effect=["A", "A", "A", "!finish"])
    @patch("quizz.stdout")
    def test_is_ready(self, mock_stdout, *_):
        q1, q2, q3, q4 = (
            Question("What?"),
            Question("What?"),
            Question("What?", required=False),
            Question("What?", required=False),
        )

        q1.pre_ask = lambda q: self.assertFalse(q.quiz.is_ready)
        q2.pre_ask = lambda q: self.assertFalse(q.quiz.is_ready)
        q3.pre_ask = lambda q: self.assertTrue(q.quiz.is_ready)
        q4.pre_ask = lambda q: self.assertTrue(q.quiz.is_ready)

        quiz = Quiz(questions=[q1, q2, q3, q4])
        quiz.start()

        mock_stdout.assert_has_calls(
            [
                call(
                    "\nYou now have answered all the required questions on"
                    " this test. You may finish, but There are still some"
                    " optional questions left (3, 4).\n"
                ),
                call("\n[Ready, some optional questions left (4).]\n"),
            ]
        )

    @patch("quizz.stdin", side_effect=["A", "A", "A", "A", "A", "!finish"])
    @patch("quizz.stdout")
    def test_is_done(self, mock_stdout, *_):
        q1, q2, q3, q4 = (
            Question("What?"),
            Question("What?"),
            Question("What?", required=False),
            Question("What?", required=False),
        )

        q1.pre_ask = q2.pre_ask = (
            lambda q: self.assertFalse(q.quiz.is_done)
            if q.attempt == 1
            else self.assertTrue(q.quiz.is_done)
        )

        q3.pre_ask = q4.pre_ask = lambda q: self.assertFalse(q.quiz.is_done)

        quiz = Quiz(questions=[q1, q2, q3, q4])
        quiz.start()

        mock_stdout.assert_has_calls(
            [
                call(
                    "\nYou now have answered all the required questions on"
                    " this test. You may finish, but There are still some"
                    " optional questions left (3, 4).\n"
                ),
                call("\n[Ready, some optional questions left (4).]\n"),
                call(
                    "\nYou now have answered all the questions on this test."
                    " You may finish or revise your questions if you want.\n"
                ),
                call("\n[Completed, waiting for finish command.]\n"),
            ]
        )

    @patch("quizz.stdin", side_effect=["", "A", "!finish"])
    @patch("quizz.stdout")
    def test_ready_done_verbosity_changes(self, *_):
        question = Question("What?", required=False)
        quiz = Quiz(questions=[question])

        self.assertFalse(hasattr(quiz, "_ready_verbose"))
        self.assertFalse(hasattr(quiz, "_done_verbose"))

        quiz.start()

        self.assertFalse(quiz._ready_verbose)
        self.assertFalse(quiz._done_verbose)

    @patch("quizz.stdin", side_effect=["!finish"])
    @patch("quizz.stdout")
    def test_pre_ask_extendable(self, *_):
        class MyQuiz(Quiz):
            def pre_ask(self):
                self.questions[self.index].answer = "Answer"
                super().pre_ask()

        question = Question("What?")
        quiz = MyQuiz(questions=[question])
        quiz.start()

        self.assertEqual("Answer", question.answer)

    def test_jump_method(self):
        q0, q1, q2, q3 = (
            MultipleChoiceQuestion("What?", choices=["a"]),
            MultipleChoiceQuestion("What?", choices=["b"]),
            MultipleChoiceQuestion("What?", choices=["c"]),
            MultipleChoiceQuestion("What?", choices=["d"]),
        )

        quiz = Quiz(questions=[q0, q1, q2, q3])

        self.assertEqual(q0, quiz.jump(0))
        self.assertEqual(q1, quiz.jump(1))
        self.assertEqual(q2, quiz.jump(2))
        self.assertEqual(q3, quiz.jump(3))


class TestCommandClass(TestCase):
    @patch("quizz.stdin", return_value="!test")
    def test_unimplemented_command(self, *_):
        class MyCommand(Command):  # noqa
            expression = "test"
            pass

        self.assertEqual("No description provided.", MyCommand.description)

        question = Question("What?", commands=[MyCommand])

        with self.assertRaisesRegex(
            NotImplementedError,
            "Define a behaviour for this command using execute method.",
        ):
            question.ask()

    @patch("quizz.stdin", side_effect=["!skip"])
    @patch("quizz.stdout")
    def test_skip(self, mock_stdout, *_):
        question = Question("Hello?", commands=[Skip], required=False)
        question.answer = "World"
        question.ask()

        mock_stdout.assert_called_with("You decided to skip this question.")

        self.assertIsNone(question.answer)
        self.assertEqual(1, question.attempt)

    @patch("quizz.stdin", side_effect=["!skip", "Answer"])
    @patch("quizz.stdout")
    def test_skip_inoperative_for_required(self, mock_stdout, *_):
        question = Question("Hello?", commands=[Skip])
        question.ask()

        mock_stdout.assert_has_calls(
            [
                call("You decided to skip this question."),
                call("This question is required."),
            ]
        )

        self.assertEqual("Answer", question.answer)
        self.assertEqual(2, question.attempt)

    @patch("quizz.stdin", side_effect=["!quit"])
    def test_quit(self, *_):
        question = Question("What", commands=[Quit])

        with self.assertRaises(SystemExit) as cm:
            question.ask()

        self.assertEqual(0, cm.exception.code)

    @patch("quizz.stdin", side_effect=["!help", "Answer"])
    @patch("quizz.stdout")
    def test_help_base(self, mock_stdout, *_):
        question = Question("What?", commands=[Help], required=False)
        question.ask()

        mock_stdout.assert_called_with(
            "\nAvailable commands are:\n!help: Shows the help message.\n"
        )
        self.assertEqual("Answer", question.answer)

    @patch("quizz.stdin", side_effect=["/help", "Answer"])
    @patch("quizz.stdout")
    def test_help_custom_message(self, mock_stdout, *_):
        question = Question(
            "What?",
            commands=[Help(message="How ya doing?."), Quit, Skip],
            command_delimiter="/",
            required=False,
        )

        question.ask()

        mock_stdout.assert_called_with(
            "How ya doing?.\nAvailable commands are:\n/help: Shows the help"
            " message.\n/quit: Quits the program.\n/skip: Skips this question"
            " without answering.\n"
        )
        self.assertEqual("Answer", question.answer)

    @patch("quizz.stdin", side_effect=["!help", "Answer"])
    @patch("quizz.stdout")
    def test_help_no_command_list(self, mock_stdout, *_):
        question = Question(
            "What?", commands=[Help(message="Howdy?", with_command_list=False)]
        )
        question.ask()

        mock_stdout.assert_called_with("Howdy?")
        self.assertEqual("Answer", question.answer)

    @patch(
        "quizz.stdin",
        side_effect=[
            "!jump",
            "!jump potato",
            "!jump 0",
            "!jump 52",
            "Ans",
            "!finish",
        ],
    )
    @patch("quizz.stdout")
    def test_jump_no_arg_or_invalid(self, mock_stdout, *_):
        question = Question("What?", commands=[Jump, Finish])
        quiz = Quiz(questions=[question])
        quiz.start()

        mock_stdout.assert_has_calls(
            [
                call("Please specify a question number to jump."),
                call("Question number needs to be a positive integer."),
                call("Question number needs to be a positive integer."),
                call("Can't jump to question 52, no such question."),
                ANY,
            ]
        )

        self.assertEqual("Ans", question.answer)

    @patch(
        "quizz.stdin",
        side_effect=[
            "!jump 4",
            "!jump 1",
            "!jump 4",
            "!jump 1",
            "Answer",
            "!finish",
        ],
    )
    @patch("quizz.stdout")
    def test_jump(self, mock_stdout, *_):
        q1, q2, q3, q4 = (
            Question("What?"),
            MultipleChoiceQuestion("What?", choices=["a"], required=False),
            MultipleChoiceQuestion("What?", choices=["c"], required=False),
            Question("What?", required=False),
        )

        quiz = Quiz(
            questions=[q1, q2, q3, q4], scheme=Scheme(commands=[Jump, Finish])
        )

        quiz.start()

        mock_stdout.assert_has_calls(
            [
                call("Jumped to question 4."),
                call("Jumped to question 1."),
                call("Jumped to question 4."),
                call("Jumped to question 1."),
                ANY,
            ]
        )

        self.assertEqual(3, q1.attempt)
        self.assertEqual(1, q2.attempt)
        self.assertEqual(2, q4.attempt)
        self.assertEqual(0, q3.attempt)
        self.assertEqual("Answer", q1.answer)

    @patch(
        "quizz.stdin",
        side_effect=list(
            itertools.chain.from_iterable(
                itertools.repeat(["!next", "!previous"], 16)
            )
        )
        + ["!finish"],
    )
    @patch("quizz.stdout")
    def test_next_previous(self, *_):
        q1, q2, q3 = (
            Question("What?"),
            Question("What? 2"),
            Question("What? 3"),
        )

        quiz = Quiz(
            questions=[q1, q2, q3],
            scheme=Scheme(commands=[Next, Previous, Finish], required=False),
        )

        quiz.start()
        self.assertEqual(17, q1.attempt)
        self.assertEqual(16, q2.attempt)
        self.assertEqual(0, q3.attempt)

    @patch("quizz.stdin", side_effect=["!finish"])
    @patch("quizz.stdout")
    def test_finish(self, *_):
        question = Question("Hello?", required=False)
        quiz = Quiz(questions=[question])
        quiz.start()

        self.assertIsNone(question.answer)
        self.assertEqual(1, question.attempt)

    @patch("quizz.stdin", side_effect=["!finish", "Answer", "Cat", "!finish"])
    @patch("quizz.stdout")
    def test_finish_error_on_uncompleted(self, mock_stdout, *_):
        q1, q2, q3 = (
            Question("Hello?"),
            Question("World?"),
            Question("Hey?", required=False),
        )

        quiz = Quiz(questions=[q1, q2, q3])
        quiz.start()

        mock_stdout.assert_has_calls(
            [
                call(
                    "There are still some required questions to answer: (1, 2)"
                ),
                ANY,
            ]
        )

        self.assertEqual("Answer", q1.answer)
        self.assertEqual("Cat", q2.answer)
        self.assertIsNone(q3.answer)

        self.assertEqual(2, q1.attempt)
        self.assertEqual(1, q2.attempt)
        self.assertEqual(1, q3.attempt)

    @patch(
        "quizz.stdin",
        side_effect=["Me", "Handsome", "", "a", "!answers", "!finish"],
    )
    @patch("quizz.stdout")
    def test_answers(self, mock_stdout, *_):
        q1, q2, q3, q4 = (
            Question("What?"),
            Question("How?"),
            Question("When?", required=False),
            MultipleChoiceQuestion("Which?", choices=["This"]),
        )

        quiz = Quiz(
            questions=[q1, q2, q3, q4],
            scheme=Scheme(commands=[Answers, Finish]),
        )
        quiz.start()

        mock_stdout.assert_has_calls(
            [
                ANY,
                call(
                    "\nCurrent answers:\n"
                    "1. What? -> [Me]\n"
                    "2. How? -> [Handsome]\n"
                    "~3. When? -> [No answer]\n"
                    "4. Which? -> [a) This]\n"
                ),
                ANY,
            ]
        )


class TestValidators(TestCase):
    def _test_validator(self, validate, bad_value, good_value):
        klass = validate.__class__.__name__

        try:
            validate(good_value)
        except ValidationError:
            self.fail("Validator failed unexpectedly: " + klass)

        with self.assertRaises(ValidationError, msg="for " + klass):
            validate(bad_value)

    def test_max_length_validator(self):
        validate = MaxLengthValidator(10)
        self._test_validator(validate, "longer_than_10", "short")

    def test_min_length_validator(self):
        validate = MinLengthValidator(10)
        self._test_validator(validate, "short", "longer_than_10")

    def test_alpha_validator(self):
        validate = AlphaValidator()
        self._test_validator(validate, "123abc", "fine")
        self._test_validator(validate, "123.abc", "good")
        self._test_validator(validate, "no spaces allowed", "q")
        self._test_validator(validate, "", "c")
        self._test_validator(validate, "  ", "fdpq")

    def test_alphanumeric_validator(self):
        validate = AlphaNumericValidator()
        self._test_validator(validate, "no spaces", "y123")
        self._test_validator(validate, "no-spacial", "13430ac")
        self._test_validator(validate, "", "0x0")
        self._test_validator(validate, "  ", "ndk")

    def test_digit_validator(self):
        validate = DigitValidator()
        self._test_validator(validate, "bad", "15928")
        self._test_validator(validate, "  ", "113")
        self._test_validator(validate, "", "93485")

    def test_regex_validator(self):
        validate = RegexValidator(r"^[a-z]+$")
        self._test_validator(validate, "", "hello")
        self._test_validator(validate, " ", "lxa")
        self._test_validator(validate, "my t", "your")
        self._test_validator(validate, "134", "bfq")
        self._test_validator(validate, "..", "cby")

    def test_inherits_validator(self):
        for klass in (
            MaxLengthValidator,
            MinLengthValidator,
            AlphaValidator,
            AlphaNumericValidator,
            DigitValidator,
            RegexValidator,
        ):
            self.assertTrue(
                issubclass(klass, Validator),
                msg=str(klass) + " is not subclass of Validator",
            )

    def test_validation_message(self):
        msg = "custom_error_message"
        validate = AlphaValidator(
            message=msg
        )  # any subclass of Validator behaves the same

        with self.assertRaisesRegex(ValidationError, msg):
            validate("not valid.")

    def test_validator_unimplemented(self):
        class MyValidator(Validator):  # noqa
            pass

        with self.assertRaises(NotImplementedError):
            MyValidator()("something")

    def test_validator_default_message(self):
        self.assertEqual("Your answer is not valid.", Validator().message)
