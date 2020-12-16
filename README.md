# quizz (WIP)

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
    
* It will append a column and a space to the end of the prompt
* It will re-ask the question in case of an empty answer
* It will strip spaces from the answer

This is due to default `Question` configuration (namely question scheme).
All of these behaviour can be customized and respectively correspond to
`append_column`, `required` and `strip` fields.

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

##### append_column `True`
A boolean, if set to `True` will append a column and space to the prompt.
For example "How are you doing?" will be asked as "How are you doing?: "

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
If the value of field defined in `Scheme` is None or an empty string (for string fields) it
will be discarded (fields of `Question` will be used).


