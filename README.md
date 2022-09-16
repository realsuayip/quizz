# quizz

[![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)](https://www.gnu.org/licenses/gpl-3.0)
[![codecov](https://codecov.io/gh/realsuayip/quizz/branch/master/graph/badge.svg?token=CKUP39Y2IW)](https://codecov.io/gh/realsuayip/quizz)

Wrappers around Python's print and input functions to create question/answer themed command line applications. See
[examples](examples) folder for real life applications.

# Documentation

### Installation

Simply install using pip:

    pip install quizz

quizz supports Python version 3.7 and onwards.

### Basic usage

Here is a basic snippet. It will prompt for the user's name and
output it in a formatted sentence, try running it yourself:

```python
from quizz import Question

question = Question("What is your name?")
question.ask()

print("Your name is: " + question.answer)
```

As you can see, this is not very useful. We could have constructed same
program with `input` function as well. As we discover more on `Question`
we will see how to exploit it to construct more useful question clauses.
If you run this snippet you will see that it behaves a bit different from
`input` function:

* It will re-ask the question in case of an empty answer
* It will strip spaces from the answer

This is due to default `Question` configuration (namely question scheme).
These behaviour can be customized and respectively correspond to
`required` and `strip` fields.

### Question fields

There are bunch of fields that define a behaviour of a question. Lets
see each of these options and what they do:

##### prompt
The prompt of the question.

##### validators
A list that contains validators or callable objects which will validate the given answers.
See Validators section to learn more.

##### options
List of `Option` objects. See Options section to learn more.

##### commands
A list that contains `Command` classes or objects. These commands will be available
in this questions context. See Commands section to learn more.

##### correct_answers
A list of strings that are counted as correct answers. The value `has_correct_answer`
of `Question` objects will depend on this list. If the correct answer is an `Option`
object, the string must correspond to `value` of the option rather than the `expression`.

Example:

```python
question = Question("1+2?", correct_answers=["3"])
question.ask()

# Assuming the answer was correct, this will be True:
is_correct = question.has_correct_answer
```

##### extra
A user defined dictionary that contains any other extra information about the question.
This is useful especially in a `Quiz` context if you want to create relations between
questions with any arbitrary data. For example, let's say you set up a quiz in which
each question has its own points. In this case you can assign point value to each question
through this field.

##### required `True`
A boolean, if `True` marks the question as required. Required questions will be asked
until the user provides a non-empty input. Otherwise the question can be left blank (in which
case the answer attribute of the question object will be None).

##### strip `True`
A boolean, if set to `True` will call `strip` function for the given input.

##### suffix
A string that will be appended to the given prompt.

##### prefix
A string that will be prepended to the given prompt.

##### command_delimiter `!`
A string that will mark the start of a command. See Commands section to learn more.

##### option_indicator `) `
A string that will determines the indicator for options. For example if set
to `]` options will be outputted as `value] expression`

#### MultipleChoiceQuestion specific fields

##### choices
A list of strings from which `Option` objects will be generated and added to
the question object. The values of options will be determined by the `style`
or `style_iterator` fields.

##### style `letter`
A string that will determine the style of option values. It can be one of these:
`letter`, `letter_uppercase`, `number`, `number_fromzero`. These styles are quite self
explanatory.

##### style_iterator
An iterable that will determine the style of option values. If provided, this will
override `style` field. Useful if you want a custom style.

##### display `horizontal`
The display style of options and values. Built-in displays are `horizontal` and `vertical`.
You may implement your own display by extending MultipleChoiceQuestion. See extending section
to learn more.

### Scheme objects

As it can be seen, there are quite several fields to define a behaviour of `Question`.
But this can be tedious if you want to use same fields for multiple questions.
This is where `Scheme` objects come in handy. `Scheme` objects can be defined just like
`Question` objects, expect `prompt` field is not required. For example:

````python
my_scheme = Scheme(required=False, commands=[Help, Skip])
question = Question("Howdy?", scheme=my_scheme)
````

You can also pass fields for `Question` even if you assign a scheme. In such case,
immutable fields will be overridden. Lists and dictionaries will be extended.
If there is a key clash in dictionary, the value given in `Question` field will be used instead.
If the value of field defined in `Scheme` is `None` it will be discarded (fields of `Question` will be used).
This behaviour is also true when applying multiple schemes.

Quizzes can also take scheme objects. In that case, each question in the
quiz will have the scheme object mounted *after their initialization*. So,
for a ``Question`` **the order of** scheme mounting can be described as:

    Question fields > Scheme of the Question > Scheme of Quiz

Keep in mind that a particular scheme will only get mounted once,
if you want to mount a scheme twice for any reason, you have to use `update_scheme` and `update`
methods while `force` and `force_scheme` keyword arguments set to `True`, respectively in the
contexts of `Question` and `Quiz`.

### Option objects
Majority of the time, the answer to a question needs to be selected from
a set of options. `Option` class is the way of defining these options. For
example:

````python
yes, no = Option(value="y", expression="Yes"), Option(value="n", expression="No")

question = Question("Are you OK?", options=[yes, no])
question.ask()

# The answer will be an Option object (yes, no)
answer = question.answer
````
In the example above, if the user inputs anything other than option
values ("y" and "n"), a `ValidationError` will occur internally and
the question will be re-asked.

Including `options` means that the question will no longer accept non-option answers,
while the validators passed through the related field will be discarded.
Also, notice that the answer is set as an `Option` object, not `str`. All of these behaviour
can be changed by overriding the `validate` and `match_option` methods of `Question`.

Keep in mind that the field `correct_answers` uses the **value** of
the `Option` to determine whether it is correct or not. This design is so,
because you might not always have the `Option` object around as you most likely
generate it in-line through list comprehensions; just like in the case
of `MultipleChoiceQuestion`. If this doesn't convince you, this behaviour
can be changed by overriding `has_correct_answer` property method of `Question`.

### Question objects

Let's inspect question objects to find out what we can do with them
before and after the answer has been given.

##### Basic attributes

| Attribute      | Description |
| ----------- | ----------- |
| answer      | The answer given to this question, set to `None` in case of no/empty answer.
| attempt     | Number of answer attempts this question had. Attempts increase when the question gets re-asked for any reason (e.g. validation errors).
| quiz        | The `Quiz` this question belongs to. Set to `None` if not found in a quiz context.
| sequence    | Index of this question in an assigned `Quiz`.
| mounted_schemes | List of schemes that are applied to this question (by any means).
| has_answer  | Shorthand for: ```question.answer is not None```
| has_correct_answer | Returns a boolean indicating whether the given answer is found in `correct_answers` field.

##### Basic methods
| Method      | Description |
| ----------- | ----------- |
| ask         | Asks the questions by calling the `input` function internally.
| update_scheme(scheme, force) | Mount given scheme object. If `force` set to `True`, signature of the scheme will be ignored.

##### Signal mechanisms

Questions can get attributes that points to a callable. This callable will be called depending
on the the type of attribute you set. We will call these *signals*. There are currently 2 signals that
can be assigned to a question: `pre_ask` and `post_answer`. As their names suggest, these signals will
be executed just before the question is asked and when the answer attribute is set, respectively.
These signals take one argument, the `Question` object. For example:

````python
question = Question("Howdy?")

# Set post_answer signal so that the answer is outputted
# just as the answer is set
question.post_answer = lambda q: print(q.answer)
question.ask()
````

Signals can be helpful especially in a quiz context where the order
of questions might be undetermined. If you want to attach a signal
to many questions, the example above might be a bit tedious. In such
a case, you can inherit from `Question` and implement
`post_answer` (or whichever signal you like) as a **staticmethod**.

##### Other notes regarding Question objects

* Avoid using `options` for MultipleChoiceQuestion as the
whole purpose of this class is to abstract away the
work on `Option` objects (through `choices`). However, `options`
and `choices` are compatible and can be used together.

* Do not refrain from extending/overriding `Question` classes
to add functionality apt to your purposes. They are
designed to be extendable.

### Quiz objects

Quiz objects are the way of packing a set of questions together. These
objects are very useful if you want to build a test-like structure, which
is generally the case. Apart from asking questions sequentially Quiz objects also
provide these functionality:

* Allows for commands such as `Next`, `Previous` and `Jump` to traverse through questions.
* Tracks whether each required or non-required questions are answered via attributes
`is_ready` and `is_done`, and outputs an info message in appropriate situations.

##### Basic attributes

| Attribute      | Description |
| ----------- | ----------- |
| index | The sequence of question that is being (or going to be) asked.
| inquiries | The sum of attempts of questions.
| questions | The list of questions on this quiz.
| scheme | The scheme of this Quiz, if none specified during initialization, this will be the default scheme.
| is_done | A boolean that indicates whether all the questions on the quiz has an answer.
| is_ready | Similar to `is_done`, but for required questions only.
| required_questions | List of required questions.
| min_inquiries | Minimum number of `Question` attempts needed before the quiz can be finished.


##### Basic methods
| Method      | Description |
| ----------- | ----------- |
| start       | Starts the quiz by asking the first question.
| update(force_scheme) | Assigns the `Quiz` object for each question on the quiz, along with its scheme. You need to call this if you mutate the list of questions after initialization.

### Commands

Commands are provided per-question basis, and they are the way of providing
meta. Commands can be executed via specified command delimiter (default `!`), and
need to be present (as classes or objects) in `commands` field.
You can create your own commands through `Command` class. Commands return an
opcode (through `opcodes` enum) which determines what to do after the execution.
Here are the available opcodes and what they do:


| opcode      | Description |
| ----------- | ----------- |
| `CONTINUE` | Re-asks the question.
| `BREAK` | Break out of the question loop, thus end the input stream.
| `JUMP`  | `Quiz` Return this along with a question sequence to ask that question next.

Aside from these opcodes, you can also return nothing (`None`), in which case
the question will not be re-asked unless it is required.

##### Built-in commands

| Command      | Expression | Description | opcode(s) returned |
| ----------- | ----------- | ------ |  ---------- |
| `Skip`      | skip | Set the answer of this question to `None` | `None`
| `Quit`      | quit | Calls `sys.exit(0)`, thus exiting the whole program. | N/A
| `Help(message="", with_command_list=True)` | help | Outputs given help message. If `with_command_list` is set to `True`, it will also output list of available commands with their description. | `CONTINUE`
| `Jump` | jump \<seq\> | Jumps to specified question. | `JUMP`
| `Next` | next | Jumps to next question. | `JUMP`
| `Previous` | previous | Jumps to previous question. | `JUMP`
| `Finish` | finish | Ends the quiz provided that all the required questions are answered. | `BREAK` or `CONTINUE`
| `Answers` | answers | Outputs the current answers for each question in the quiz. | `CONTINUE`

### Validators

Validators validate the input given to a question. `ValidationError` is the
exception class to be raised when the given input is not valid. Here is an
example implementation of a validator:

````python
from quizz import ValidationError, Question

def validate_word_count(answer):
    # Check if the answer has at least 5 words.
    count = len(answer.split())

    if count < 5:
        raise ValidationError("Your answer needs at least 5 words!")

question = Question("Name 5 or more mammals.", validators=[validate_word_count])
````

The example above will check if the word has at least 5 words. If the
user inputs a non-valid string the question will be re-asked until a
valid answer has been given.

Quizz also provides class-based validators (from which all the built-in validators
inherit). You can use `Validator` class to create your own class-based validators, which
can also take arguments.

##### Built-in validators

Built-in validators are:

* `MaxLengthValidator`
* `MinLengthValidator`
* `AlphaValidator`
* `AlphaNumericValidator`
* `DigitValidator`
* `RegexValidator`

By default, class based validators take two keyword arguments: `against` and `message`.
`against` is the value to be tested against, for example `MaxLengthValidator`'s max
length or  `RegexValidator`'s regex pattern.
