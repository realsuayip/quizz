from unittest import TestCase
from unittest.mock import patch


from quizz import (
    ValidationError,
    MaxLengthValidator,
    MinLengthValidator,
    AlphaValidator,
    AlphaNumericValidator,
    DigitValidator,
    RegexValidator,
    Validator,
    Question,
    Option,
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
