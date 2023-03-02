import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="quizz",
    version="1.0.0",
    author="Şuayip Üzülmez",
    author_email="suayip.541@gmail.com",
    description="Wrappers around Python's print and input functions to create"
    " question/answer themed command line applications.",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/realsuayip/quizz",
    packages=setuptools.find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: GNU General Public License v3 (GPLv3)",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.7",
)
