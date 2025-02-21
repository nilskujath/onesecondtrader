import yaml


def load_config():
    with open("pdengine_config.yaml", "r") as config:
        return yaml.safe_load(config)


def main(config):
    print(config["test_message_2"]["nested_test_message"])


if __name__ == "__main__":
    config = load_config()
    main(config)
