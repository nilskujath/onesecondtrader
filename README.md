# OneSecondTrader

## Installation

Clone the application from GitHub:
```shell
git clone https://github.com/nilskujath/onesecondtrader.git
```

Run it via the following shell script
```shell
bash devrun.sh
```


## Design Choices

### YAML Configuration

The code is designed in such a way that it should not be necessary to edit the existing code by modifying function arguments. Instead, there is one configuration file in `yaml` format on a per-service basis that allows the configuration of all parameters that are intended to be user-modifiable.

Consider for example the `pdengine` service. There will be a file named `pdengine_config.yaml` (i.e., following the schema `<service_name>_config.yaml`) that is meant to be edited by the user that will look something like this (dummy implementation):

```yaml
test_message_1: "Hello, World!"
test_message_2:
  nested_test_message: "Hello, World!"
```

The python files that are associated with that service will then work in the following manner (again: this is a dummy implementation to illustrate the principle):

```python
import yaml


def load_config():
    with open("pdengine_config.yaml", "r") as config:
        return yaml.safe_load(config)


def main(config):
    print(config["test_message_2"]["nested_test_message"])


if __name__ == "__main__":
    config = load_config()
    main(config)
```

That is, there is a function `load_config` that will return the config as a (nested) dictionary, i.e.:
```python
{'test_message_1': 'Hello, World!', 'test_message_2': {'nested_test_message': 'Hello, World!'}}
```
We can then pick out the arguments we want, e.g.: `config["test_message_2"]["nested_test_message"]` will yield the string `'Hello, World!'` in our example.

The possible values of a given field in the `pdengine_config.yaml` file are validated via internal enums.


## Development

After having cloned the repository (see section: 'Installation'), activate the poetry environment (you will need to have `poetry` installed) by running:

```shell
poetry env activate
```

Before committing to git, please run:
```shell
poetry run black .
```
