from unittest import TestCase
from unittest.mock import call, patch

from quizz import (
    AlphaNumericValidator,
    AlphaValidator,
    Command,
    DigitValidator,
    Help,
    MaxLengthValidator,
    MinLengthValidator,
    Option,
    Question,
    RegexValidator,
    Scheme,
    Skip,
    ValidationError,
    Validator,
    opcodes,
)


class TestQuestion(TestCase):
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
        self.assertTrue(question.append_column)

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

    @patch("quizz.stdin")
    def test_append_column(self, mock_stdin):
        mock_stdin.return_value = "Answer"

        question = Question("What?")
        question_with_no_column = Question("What?", append_column=False)

        self.assertTrue(question.get_append_column())
        self.assertFalse(question_with_no_column.get_append_column())

        self.assertEqual("What?: ", question.get_prompt())
        self.assertEqual("What?", question_with_no_column.get_prompt())

        question.ask()
        mock_stdin.assert_called_with("What?: ")

        question_with_no_column.ask()
        mock_stdin.assert_called_with("What?")

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

    def test_scheme_skips_empty_strings(self):
        my_scheme = Scheme(prompt="", option_indicator="")
        question = Question("What?", scheme=my_scheme)

        self.assertEqual("What?", question.prompt)
        self.assertEqual(") ", question.option_indicator)

    def test_scheme_overrides_immutable(self):
        my_scheme = Scheme(
            prompt="Whats up?",
            required=False,
            strip=False,
            append_column=False,
            command_delimiter="x",
            option_indicator="-",
        )

        question = Question("What?", scheme=my_scheme)

        self.assertEqual("Whats up?", question.prompt)
        self.assertEqual("x", question.command_delimiter)
        self.assertEqual("-", question.option_indicator)

        self.assertFalse(question.required)
        self.assertFalse(question.strip)
        self.assertFalse(question.append_column)

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
