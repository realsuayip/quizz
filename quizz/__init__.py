"""
quizz - Library to create interactive question/answer themed console programs.
Copyright (C) 2020 Şuayip Üzülmez <suayip.541@gmail.com>

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <https://www.gnu.org/licenses/>.
"""

from __future__ import annotations

import itertools
import re
import string
import sys

from dataclasses import dataclass, field, fields
from enum import Enum
from typing import (
    Any,
    Callable,
    Dict,
    Generator,
    Iterable,
    List,
    Optional,
    Tuple,
    Type,
    Union,
    cast,
)

__version__ = "1.0.0"

__all__ = [
    "AlphaNumericValidator",
    "AlphaValidator",
    "Answers",
    "Command",
    "DigitValidator",
    "Finish",
    "Help",
    "Jump",
    "MaxLengthValidator",
    "MinLengthValidator",
    "MultipleChoiceQuestion",
    "Next",
    "opcodes",
    "Option",
    "Previous",
    "Question",
    "Quit",
    "Quiz",
    "RegexValidator",
    "Scheme",
    "Skip",
    "ValidationError",
    "Validator",
]

###############
# BASE MODULE #
###############

stdin = input
stdout = print


def signal_hook(obj: Any, method: str) -> None:
    """
    Call this method if this method is attribute of obj.
    Used to call question signals. Method should be static, the
    first argument takes the object itself.
    """

    if callable(getattr(obj, method, None)):
        getattr(obj, method)(obj)


def number_iterator(start: int) -> Generator[str, None, None]:
    for num in itertools.count(start=start):
        yield str(num)


@dataclass
class Scheme:
    """
    An empty Scheme encompassing all of the Question &
    MultipleChoiceQuestion fields.
    """

    # Question
    prompt: Optional[str] = None

    validators: Optional[List[Callable[[str], None]]] = None
    options: Optional[List[Option]] = None
    commands: Optional[List[Union[Command, Type[Command]]]] = None
    correct_answers: Optional[List[str]] = None
    extra: Optional[dict[Any, Any]] = None

    required: Optional[bool] = None
    strip: Optional[bool] = None

    suffix: Optional[str] = None
    prefix: Optional[str] = None

    command_delimiter: Optional[str] = None
    option_indicator: Optional[str] = None

    # MultipleChoiceQuestion
    choices: Optional[List[str]] = None
    display: Optional[str] = None
    style: Optional[str] = None
    style_iterator: Optional[Iterable[str]] = None


_field_names: List[str] = [f.name for f in fields(Scheme)]


@dataclass
class Option:
    """
    Option dataclass. Primarily used in MultipleChoiceQuestion but
    not limited to.
    """

    value: str
    expression: str


@dataclass
class Question:
    """
    A question dataclass decorated with variety of methods
    to mutate its attributes & handle I/O.
    """

    prompt: str

    validators: List[Callable[[str], None]] = field(default_factory=list)
    options: List[Option] = field(default_factory=list)
    commands: List[Union[Command, Type[Command]]] = field(default_factory=list)
    correct_answers: List[str] = field(default_factory=list)
    extra: dict[Any, Any] = field(default_factory=dict)

    required: bool = True
    strip: bool = True

    suffix: str = ""
    prefix: str = ""

    command_delimiter: str = "!"
    option_indicator: str = ") "

    scheme: Optional[Scheme] = None
    """
    Questions may take a Scheme object to override the its base. This is
    done so that you can define your own generic Scheme instead of passing
    keyword arguments each time you create a new question.

    The overriding behaviour changes depending on the field type. Immutable
    values are replaced. List are extended, dictionaries get merged but keys
    defined on question initialization take precedence.
    """

    def __post_init__(self) -> None:
        if not self.prompt:
            raise ValueError("A question should at least define a prompt.")

        self.answer: Optional[Union[str, Option]] = None
        self.attempt: int = 0
        """Each time this question is asked, this gets incremented by 1."""

        self.quiz: Optional[Quiz] = None
        """
        Quiz this question is assigned to. This will be set if the question
        is mentioned in 'questions' keyword argument on Quiz initialization.
        If the question is added externally (i.e. through the mutation of
        Quiz.questions), the update() method of the quiz needs to be called
        so that the question can be assigned to Quiz.

        Alternatively you may assign this manually, in which case the scheme
        of the quiz will not be applied, unlike in update method.
        """

        self.mounted_schemes: List[Scheme] = []
        """
        List of Scheme objects that are applied to this question through
        update_scheme method. Duplicate schemes may be found if the method is
        called with force=True.
        """

        if self.scheme is not None:
            self.update_scheme(self.scheme)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Question):
            return NotImplemented

        return id(self) == id(other)

    def __str__(self) -> str:
        return "<%s: %s>" % (self.__class__.__name__, self.prompt)

    def update_scheme(self, scheme: Scheme, force: bool = False) -> None:
        """Update this object based on a given scheme object."""

        if (scheme in self.mounted_schemes) and not force:
            return

        for name in _field_names:
            value = getattr(scheme, name)

            if (value is None) or (not hasattr(self, name)):
                continue

            if isinstance(value, list):
                setattr(self, name, [*getattr(self, name), *value])
            elif isinstance(value, dict):
                # This question's dict keys takes precedence
                setattr(self, name, {**value, **getattr(self, name)})
            else:
                setattr(self, name, value)

        self.mounted_schemes.append(scheme)

    def _ask(self) -> Optional[Union[opcodes, Tuple[opcodes, Any]]]:
        """
        Internal ask method for: setting real input, getting command opcodes,
        validation and setting up signals.
        """

        self.attempt += 1
        signal_hook(self, "pre_ask")

        answer: Optional[Union[str, Option]]

        answer = stdin(self.get_prompt())
        strip = answer.strip()

        if self.get_strip():
            answer = strip

        # Command execution
        if len(strip) > 1 and strip.startswith(self.command_delimiter):
            return self.execute_command(strip[1:])

        # Validation
        try:
            options = self.get_options()

            if options:
                answer = self.match_option(strip, options)
            else:
                self.validate(answer)

        except ValidationError as exc:
            stdout(str(exc))
            return opcodes.CONTINUE

        # Set answer
        self.answer = answer or self.answer or None

        signal_hook(self, "post_answer")
        return None

    def validate(self, answer: str) -> None:
        for validate in self.validators:
            validate(answer)

    def match_option(self, value: str, options: List[Option]) -> Option:
        try:
            return next(option for option in options if value == option.value)
        except StopIteration as exc:
            raise ValidationError(
                "\nThe selected option is not valid."
                " Available options are: %s\n"
                % "".join(
                    "\n%s%s%s"
                    % (
                        option.value,
                        self.option_indicator,
                        option.expression,
                    )
                    for option in options
                )
            ) from exc

    def ask(self) -> None:
        """
        Public ask method for: traversing through questions, associating
        questions with Quizzes, handling opcodes from commands, checking for
        "required" attribute.
        """

        if self.quiz is not None:
            self.quiz.index = self.sequence
            self.quiz.inquiries += 1
            self.quiz.pre_ask()

        response = self._ask()

        op: Optional[opcodes]
        args: List[Any]

        if isinstance(response, tuple):
            op, *args = response
        else:
            op = response

        if op == opcodes.JUMP:
            assert self.quiz is not None, "Missing quiz object for %s" % self
            return self.quiz.jump(*args).ask()  # noqa

        if op == opcodes.CONTINUE:
            return self.ask()

        if op == opcodes.BREAK:
            return

        required = self.get_required()

        if required and not self.has_answer:
            stdout("This question is required.")
            return self.ask()

        if self.quiz is not None:
            return self.quiz.jump(self.quiz.index + 1).ask()

    @property
    def sequence(self) -> int:
        """Sequence of this question in Quiz object."""

        if self.quiz is None:
            return 0

        return self.quiz.questions.index(self)

    @property
    def has_answer(self) -> bool:
        return self.answer is not None

    @property
    def has_correct_answer(self) -> bool:
        if not self.has_answer:
            return False

        answer = self.answer

        if isinstance(self.answer, Option):
            answer = self.answer.value

        return answer in self.get_correct_answers()

    def execute_command(
        self, request: str
    ) -> Optional[Union[opcodes, Tuple[opcodes, Any]]]:
        """
        For inputs starting with command delimiter, check
        if such command exists, execute it if so, and return the opcode.

        :param request: Complete command string (with arguments).
        """

        commands = self.get_commands()

        # Expression is the word until the first space, remaining words
        # are parsed as arguments and sent to the command.
        expression: str
        args: List[str]
        expression, *args = request.split()  # ^ PEP 526 ^

        if not commands:
            stdout("Commands are disabled for this question.")
            return opcodes.CONTINUE

        try:
            command = next(c for c in commands if c.expression == expression)
            return command().execute(self, *args)
        except StopIteration:
            stdout("Command not found: %s" % expression)
            return opcodes.CONTINUE

    def get_prompt(self) -> str:
        prompt = "".join((self.get_prefix(), self.prompt, self.get_suffix()))

        if self.quiz is not None:
            prompt = self.get_question_pre() + prompt

        return prompt

    def get_question_pre(self) -> str:
        """
        In a Quiz context, get question metadata for output.
        """
        assert self.quiz is not None, "Missing quiz object for %s" % self

        current_answer = (
            (
                "%s%s%s"
                % (
                    self.answer.value,
                    self.option_indicator,
                    self.answer.expression,
                )
                if isinstance(self.answer, Option)
                else self.answer
            )
            if self.has_answer
            else "No answer"
        )

        return "* Question %d/%d. [%s]\n" % (
            self.sequence + 1,
            len(self.quiz.questions),
            current_answer,
        )

    def get_strip(self) -> bool:
        return self.strip

    def get_suffix(self) -> str:
        return self.suffix

    def get_prefix(self) -> str:
        return self.prefix

    def get_options(self) -> List[Option]:
        return self.options

    def get_commands(self) -> List[Union[Command, Type[Command]]]:
        return self.commands

    def get_required(self) -> bool:
        return self.required

    def get_correct_answers(self) -> List[str]:
        return self.correct_answers


@dataclass
class MultipleChoiceQuestion(Question):
    """
    A Question which provides a simple interface to create multiple choice
    questions.
    """

    choices: List[str] = field(default_factory=list)
    display: Optional[str] = "horizontal"
    style: str = "letter"
    style_iterator: Optional[Iterable[str]] = None

    def __post_init__(self) -> None:
        self.primitive_options = self.options

        super().__post_init__()
        self.update_options()

        if not self.get_options():
            raise ValueError(
                "MultipleChoiceQuestion should at least have one"
                " member in 'options' or 'choices' attributes."
            )

    def update_scheme(self, scheme: Scheme, force: bool = False) -> None:
        super().update_scheme(scheme, force)

        if scheme.options is not None:
            self.primitive_options += scheme.options

        self.update_options()

    def update_options(self) -> None:
        """Creates Options from choices."""

        self.options = [
            Option(value=str(value), expression=expression)
            for value, expression in zip(
                self.get_style_iterator(), self.choices
            )
        ] + self.primitive_options

    def get_style_iterator(self) -> Iterable[str]:
        """
        A style iterator is any iterable that provides strings for option
        styles. For example "love" will output l) choice1 o) choice2 etc.
        """

        styles: Dict[str, Iterable[str]] = {
            "letter": string.ascii_letters,
            "letter_uppercase": string.ascii_uppercase,
            "number": number_iterator(start=1),
            "number_fromzero": number_iterator(start=0),
        }

        # Check self.style for built-in styles, else look for a style_iterator.
        style_iterator = (
            self.style_iterator
            if self.style_iterator is not None
            else styles.get(self.style)
        )

        if style_iterator is None:
            raise ValueError(
                "Unknown style or invalid style iterator."
                " Built-in styles are: (%s)" % ", ".join(styles.keys())
            )

        return style_iterator

    def get_display(self) -> Optional[str]:
        return self.display

    def get_prompt(self) -> str:
        prompt = super().get_prompt()
        display = self.get_display()

        if display is None:
            return prompt

        if not hasattr(self, "get_%s_display" % display):
            raise NotImplementedError(
                "There is no such display '%(display)s'. Built-in displays"
                " are: (vertical, horizontal). You may create this display"
                " by implementing get_%(display)s_display method."
                % {"display": display}
            )

        return cast(str, getattr(self, "get_%s_display" % display)(prompt))

    def _option_format(self) -> Iterable[str]:
        return (
            "%s%s%s" % (option.value, self.option_indicator, option.expression)
            for option in self.options
        )

    def _sep_format(self, prompt: str, sep: str) -> str:
        return "%s\n%s\nYour answer: " % (
            prompt,
            sep.join(self._option_format()),
        )

    def get_horizontal_display(self, prompt: str) -> str:
        return self._sep_format(prompt, "  ")

    def get_vertical_display(self, prompt: str) -> str:
        return self._sep_format(prompt, "\n")


class Quiz:
    """
    An object to queue questions. Supports useful commands such as
    Next, Previous, Jump to traverse easily among questions.

    When all the (required) questions are answered in a Quiz, apt
    message will be outputted to guide the user.
    """

    def __init__(
        self, questions: List[Question], scheme: Union[Scheme, None] = None
    ) -> None:
        """
        :param questions: A list of question objects.
        :param scheme: Quizzes also take scheme, this scheme will be
        applied to each question on the quiz upon its initialization (with the
        same manner of Question's scheme).
        """

        self.index: int = 0
        """
        Index of current question. This index will change upon Question.ask
        method, which traverses through questions.
        """

        self.inquiries: int = 0
        """
        The number of times a question is asked in this test. When this number
        reaches the required number of questions (min_inquiries), Quiz will
        start to test if the test is ready/done.
        """

        default_scheme = Scheme(commands=[Finish])
        self.scheme = scheme if scheme is not None else default_scheme
        """
        The scheme of this Quiz. This scheme will be mounted to each question
        assigned to this, if exact scheme object is not mounted before.
        """

        self.questions = questions
        self.update()

    def update(self, force_scheme: bool = False) -> None:
        for question in self.questions:
            question.quiz = self
            question.update_scheme(self.scheme, force=force_scheme)

    def start(self) -> None:
        """
        Starts the quiz by asking the first question.
        """
        self.questions[self.index].ask()

    @property
    def min_inquiries(self) -> int:
        return len(self.required_questions)

    @property
    def required_questions(self) -> List[Question]:
        return [question for question in self.questions if question.required]

    @property
    def is_ready(self) -> bool:
        """A quiz is ready when all of its REQUIRED questions are answered."""
        if self.inquiries < self.min_inquiries:
            return False

        return all(question.has_answer for question in self.required_questions)

    @property
    def is_done(self) -> bool:
        """A quiz is done when all of its questions are answered."""
        return self.is_ready and all(
            question.has_answer for question in self.questions
        )

    def jump(self, index: int) -> Question:
        try:
            return self.questions[index]
        except IndexError:
            return self.questions[0]

    def pre_ask(self) -> None:
        """
        This method is called just before a question gets asked in the quiz to
        test if the quiz is ready/done. You may override this method to apply
        custom logic.
        """

        if self.is_done:
            self.done()
        elif self.is_ready:
            self.ready()

    def ready(self) -> None:
        """
        This method is called when the quiz is ready. Outputs an useful
        message, verbosity of this message changes after first time.
        """

        verbose = self._get_verbosity("_ready_verbose")
        message = self.get_ready_message(verbose)
        stdout(message)

        self._ready_verbose: bool = False  # noqa

    def done(self) -> None:
        """
        This method is called when the quiz is done. Outputs an useful message,
        verbosity of this message changes after first time.
        """

        verbose = self._get_verbosity("_done_verbose")
        message = self.get_done_message(verbose)
        stdout(message)

        self._done_verbose: bool = False  # noqa

    def _get_verbosity(self, name: str) -> bool:
        return cast(bool, getattr(self, name)) if hasattr(self, name) else True

    def get_ready_message(self, verbose: bool) -> str:
        sequences = ", ".join(
            str(q.sequence + 1)
            for q in self.questions
            if not any([q.required, q.has_answer])
        )

        if verbose:
            return (
                "\nYou now have answered all the required questions on this"
                " test. You may finish, but There are still some optional"
                " questions left (%s).\n" % sequences
            )

        return "\n[Ready, some optional questions left (%s).]\n" % sequences

    def get_done_message(self, verbose: bool) -> str:  # noqa
        if verbose:
            return (
                "\nYou now have answered all the questions on this test. "
                "You may finish or revise your questions if you want.\n"
            )

        return "\n[Completed, waiting for finish command.]\n"


#############
# COMMANDS #
#############


class opcodes(Enum):
    """
    Opcodes for commands.

    JUMP: Return this opcode with a question sequence to ask that question
    in a quiz context.

    CONTINUE: Return this opcode in a command to re-ask the current question.
    BREAK: Return this opcode to forcibly break out of question loop.

    Returning no opcode in a command will execute the command but the question
    will not be re-asked, in which case answer will be None (if not answered
    previously).
    """

    CONTINUE = 0
    BREAK = 1
    JUMP = 2


class Command:
    expression: str = ""
    description: str = "No description provided."

    def __call__(self, *args: Any, **kwargs: Any) -> Command:
        return self

    def execute(
        self, question: Question, *args: str
    ) -> Optional[Union[opcodes, Tuple[opcodes, Any]]]:
        raise NotImplementedError(
            "Define a behaviour for this command using execute method."
        )


class Skip(Command):
    expression = "skip"
    description = "Skips this question without answering."

    def execute(self, question: Question, *args: Any) -> None:
        stdout("You decided to skip this question.")
        question.answer = None


class Quit(Command):
    expression = "quit"
    description = "Quits the program."

    def execute(self, question: Question, *args: Any) -> None:
        sys.exit(0)


class Help(Command):
    expression = "help"
    description = "Shows the help message."

    def __init__(self, message: str = "", with_command_list: bool = True):
        self.message = message
        self.with_command_list = with_command_list

    def execute(self, question: Question, *args: Any) -> opcodes:
        stdout(self.get_message(question))
        return opcodes.CONTINUE

    def get_message(self, question: Question) -> str:
        return self.message + self.get_available_commands(question)

    def get_available_commands(self, question: Question) -> str:
        if not self.with_command_list:
            return ""

        delimiter = question.command_delimiter

        return "\nAvailable commands are:\n%s" % (
            "".join(
                "%s%s: %s\n" % (delimiter, cmd.expression, cmd.description)
                for cmd in question.commands
            ),
        )


class Jump(Command):
    expression = "jump"
    description = "Jumps to specified question. Usage: jump <number>"

    def execute(
        self, question: Question, *args: Any
    ) -> Union[opcodes, Tuple[opcodes, int]]:
        if not args:
            stdout("Please specify a question number to jump.")
            return opcodes.CONTINUE

        jump_to = args[0]

        is_digit = jump_to.isdigit()
        is_positive = is_digit and int(jump_to) > 0

        if not (is_digit and is_positive):
            stdout("Question number needs to be a positive integer.")
            return opcodes.CONTINUE

        number = int(jump_to)

        assert question.quiz is not None
        if number > len(question.quiz.questions):
            stdout("Can't jump to question %s, no such question." % number)
            return opcodes.CONTINUE

        stdout("Jumped to question %s." % jump_to)
        return opcodes.JUMP, number - 1


class Next(Command):
    expression = "next"
    description = "Jumps to next question."

    def execute(self, question: Question, *args: Any) -> Tuple[opcodes, int]:
        assert question.quiz is not None
        return opcodes.JUMP, question.quiz.index + 1


class Previous(Command):
    expression = "previous"
    description = "Jumps to previous question."

    def execute(self, question: Question, *args: Any) -> Tuple[opcodes, int]:
        assert question.quiz is not None
        return opcodes.JUMP, question.quiz.index - 1


class Finish(Command):
    expression = "finish"
    description = "Finishes the quiz."

    def execute(self, question: Question, *args: Any) -> opcodes:
        assert question.quiz is not None
        if question.quiz.is_ready:
            return opcodes.BREAK

        stdout(
            "There are still some required questions to answer: (%s)"
            % ", ".join(
                str(q.sequence + 1)
                for q in question.quiz.required_questions
                if not q.has_answer
            )
        )
        return opcodes.CONTINUE


class Answers(Command):
    expression = "answers"
    description = "Shows the current answers for each question in the quiz."

    def execute(self, question: Question, *args: Any) -> opcodes:
        assert question.quiz is not None
        clauses_with_answers = "\n".join(
            "%d. %s -> [%s]"
            % (
                q.sequence + 1,
                q.prompt,
                (
                    str(q.answer.value)
                    + str(q.option_indicator)
                    + str(q.answer.expression)
                )
                if isinstance(q.answer, Option)
                else q.answer,
            )
            if q.has_answer
            else "~%d. %s -> [No answer]" % (q.sequence + 1, q.prompt)
            for q in question.quiz.questions
        )

        stdout("\nCurrent answers:\n%s\n" % clauses_with_answers)
        return opcodes.CONTINUE


##############
# VALIDATORS #
##############


class ValidationError(Exception):
    """
    Raise this in a validator to indicate that the answer is not valid.
    """


class Validator:
    def __init__(
        self, against: Any = None, message: Union[str, None] = None
    ) -> None:
        self.against = against
        self.message: str = (
            message if message is not None else "Your answer is not valid."
        )

    def __call__(self, value: str) -> None:
        if not self.is_valid(value):
            raise ValidationError(self.message)

    def is_valid(self, value: str) -> bool:
        raise NotImplementedError(
            "You need to define your validation logic in is_valid method."
        )


class MaxLengthValidator(Validator):
    def is_valid(self, value: str) -> bool:
        return len(value) <= cast(int, self.against)


class MinLengthValidator(Validator):
    def is_valid(self, value: str) -> bool:
        return len(value) >= cast(int, self.against)


class AlphaValidator(Validator):
    def is_valid(self, value: str) -> bool:
        return value.isalpha()


class AlphaNumericValidator(Validator):
    def is_valid(self, value: str) -> bool:
        return value.isalnum()


class DigitValidator(Validator):
    def is_valid(self, value: str) -> bool:
        return value.isdigit()


class RegexValidator(Validator):
    def is_valid(self, value: str) -> bool:
        return bool(re.match(self.against, value))
