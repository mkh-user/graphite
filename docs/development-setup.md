# How to set up Graphite for development

This document shows how you can set up Graphite project for development tasks.

## Step 1: Fork repository

If you want to contribute to Graphite, you should create a fork first:

**[Fork Graphite from this link](https://github.com/mkh-user/graphite/fork)**

## Step 2: Clone repository

- [Install Git](https://git-scm.com/book/en/v2/Getting-Started-Installing-Git).
- Open terminal in the directory you want to keep project in.
- Clone git repository: (Replace `user-name/graphite` with correct path to your fork)
```shell
git clone https://github.com/user-name/graphite.git
```

> **Note:**  
> You need a [GitHub](https://github.com) account to **contribute** in Graphite.

## Step 3: Install dependencies

- [Install Python](https://www.python.org/downloads/). (Works on `3.9` to `3.14`)
- Open terminal in project directory.
- Install required Python packages with optional development and benchmark dependencies:
```shell
pip install ".[dev, benchmark]"
```

---

## Tips

### Creating separated branches

Always create an up-to-date branch when you need to work on a feature or bug fix.

- Open terminal in project directory.
- [Update your fork's `dev` branch.](https://stackoverflow.com/questions/7244321/how-do-i-update-or-sync-a-forked-repository-on-github)
- Checkout `dev` branch:
```shell
git checkout dev
```
- Create a new branch: (Replace `<new-branch-name>` with your branch name (without `<>`))
```shell
git checkout -b <new-branch-name>
```
- Start editing.

### Running checks

Always run checks before push to development branches.

- Open terminal in project directory.
- Run this command to ensure you have `pylint`, `pytest`, and `ty`:
```shell
pip install ".[dev]"
```
- Lint code with pylint and modify your code until it get **10.00/10** rating:
```shell
pylint $(git ls-files '*.py')
```
- Change directory to `tests/` with `cd tests`.
- Run tests and unsure all are passed:
```shell
pytest
```
- Use ty to check types:
```shell
ty check
```

### Running benchmarks

Run benchmarks before / after your changes to measure performance impacts.

- Open terminal in project directory.
- Run this command to ensure you have benchmark dependencies:
```shell
pip install ".[benchmark]"
```
- Change directory to `tests/` with `cd tests/`
- Run benchmark (append `--help` to get more information):
```shell
python benchmark.py
```
