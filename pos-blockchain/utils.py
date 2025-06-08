# Copyright (c) 2025 An Hongxu
# Peking University - School of Software and Microelectronics
# Email: anhongxu@stu.pku.edu.cn
#
# For academic use only. Commercial usage is prohibited without authorization.

import yaml

def load_config(path="config.yaml", section=None):
    """Load configuration from a YAML file."""
    with open(path, "r") as f:
        config = yaml.safe_load(f)

    if section:
        return config.get(section, {})
    return config
