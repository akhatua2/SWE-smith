import re

from dataclasses import dataclass, field
from swebench.harness.constants import TestStatus
from swesmith.constants import ENV_NAME
from swesmith.profiles.base import RepoProfile, registry


@dataclass
class PhpProfile(RepoProfile):
    """
    Profile for PHP repositories.
    """

    org_dh: str = "swebench"
    test_cmd: str = "vendor/bin/phpunit --testdox --colors=never"
    exts: list[str] = field(default_factory=lambda: [".php"])


@dataclass
class Dbal(PhpProfile):
    owner: str = "doctrine"
    repo: str = "dbal"
    commit: str = "acb68b388b2577bb211bb26dc22d20a8ad93d97d"

    @property
    def dockerfile(self):
        return f"""FROM php:8.3
RUN apt-get update && \
    apt-get install -y wget git build-essential unzip libgd-dev libzip-dev libgmp-dev libftp-dev libcurl4-openssl-dev libpq-dev libsqlite3-dev && \
    docker-php-ext-install pdo pdo_mysql pdo_pgsql pdo_sqlite mysqli gd zip gmp ftp curl pcntl && \
    apt-get -y autoclean && \
    rm -rf /var/lib/apt/lists/*

RUN curl -sS https://getcomposer.org/installer | php -- --2.2 --install-dir=/usr/local/bin --filename=composer

RUN git clone https://github.com/{self.mirror_name} /{ENV_NAME}
WORKDIR /{ENV_NAME}
RUN composer update
RUN composer install
"""

    def log_parser(self, log: str) -> dict[str, str]:
        return parse_log_phpunit_testdox(log)


def parse_log_phpunit_testdox(log: str) -> dict[str, str]:
    """Parse PHPUnit --testdox output format."""
    test_status_map = {}
    passed_pattern = re.compile(r"^\s*✔\s*(.+)$")
    failed_pattern = re.compile(r"^\s*✘\s*(.+)$")
    skipped_pattern = re.compile(r"^\s*↩\s*(.+)$")
    for line in log.split("\n"):
        for pattern, status in (
            (passed_pattern, TestStatus.PASSED.value),
            (failed_pattern, TestStatus.FAILED.value),
            (skipped_pattern, TestStatus.SKIPPED.value),
        ):
            match = pattern.match(line)
            if match:
                test_name = match.group(1).strip()
                test_status_map[test_name] = status
                break
    return test_status_map


def parse_log_phpunit_verbose(log: str) -> dict[str, str]:
    """Parse PHPUnit --verbose (non-testdox) output format.

    Matches lines like:
    ✓ testMethodName
    ✗ testMethodName
    Or standard verbose format:
    OK (42 tests, 100 assertions)
    FAILURES!
    Tests: 42, Assertions: 100, Failures: 2.
    """
    test_status_map = {}
    # Match individual test results in verbose mode
    # Format: "Test\\Namespace\\Class::testMethod"
    passed = re.compile(r"^\s*✓\s*(.+)$")
    failed = re.compile(r"^\s*✗\s*(.+)$")
    # Also match standard PHPUnit output lines
    std_pass = re.compile(r"^ok \d+ - (.+)$", re.IGNORECASE)
    std_fail = re.compile(r"^not ok \d+ - (.+)$", re.IGNORECASE)
    for line in log.split("\n"):
        for pattern, status in (
            (passed, TestStatus.PASSED.value),
            (failed, TestStatus.FAILED.value),
            (std_pass, TestStatus.PASSED.value),
            (std_fail, TestStatus.FAILED.value),
        ):
            match = pattern.match(line)
            if match:
                test_name = match.group(1).strip()
                test_status_map[test_name] = status
                break
    return test_status_map


@dataclass
class Guzzlefb92d95f(PhpProfile):
    owner: str = "guzzle"
    repo: str = "guzzle"
    commit: str = "fb92d95f80a9da51bf8f2a5b26d8e8ea3b6d99ed"

    @property
    def dockerfile(self):
        return f"""FROM php:8.3
RUN apt-get update && \
    apt-get install -y git unzip libcurl4-openssl-dev libzip-dev nodejs npm && \
    docker-php-ext-install curl zip && \
    apt-get -y autoclean && \
    rm -rf /var/lib/apt/lists/*
RUN curl -sS https://getcomposer.org/installer | php -- --install-dir=/usr/local/bin --filename=composer
RUN git clone https://github.com/{self.mirror_name} /{ENV_NAME}
WORKDIR /{ENV_NAME}
RUN composer install
"""

    def log_parser(self, log: str) -> dict[str, str]:
        return parse_log_phpunit_testdox(log)


@dataclass
class Monolog6db20ca0(PhpProfile):
    owner: str = "Seldaek"
    repo: str = "monolog"
    commit: str = "6db20ca029219dd8de378cea8e32ee149399ef1b"

    @property
    def dockerfile(self):
        return f"""FROM php:8.3
RUN apt-get update && \
    apt-get install -y git unzip libcurl4-openssl-dev && \
    docker-php-ext-install curl sockets && \
    apt-get -y autoclean && \
    rm -rf /var/lib/apt/lists/*
RUN curl -sS https://getcomposer.org/installer | php -- --install-dir=/usr/local/bin --filename=composer
RUN git clone https://github.com/{self.mirror_name} /{ENV_NAME}
WORKDIR /{ENV_NAME}
RUN composer install --ignore-platform-req=ext-mongodb
"""

    def log_parser(self, log: str) -> dict[str, str]:
        return parse_log_phpunit_testdox(log)


@dataclass
class PhpParser50f0d9c9(PhpProfile):
    owner: str = "nikic"
    repo: str = "PHP-Parser"
    commit: str = "50f0d9c9d0e3cff1163c959c50aaaaa4a7115f08"

    @property
    def dockerfile(self):
        return f"""FROM php:8.3
RUN apt-get update && \
    apt-get install -y git unzip && \
    apt-get -y autoclean && \
    rm -rf /var/lib/apt/lists/*
RUN curl -sS https://getcomposer.org/installer | php -- --install-dir=/usr/local/bin --filename=composer
RUN git clone https://github.com/{self.mirror_name} /{ENV_NAME}
WORKDIR /{ENV_NAME}
ENV COMPOSER_ROOT_VERSION=5.99.99
RUN composer install --no-interaction
"""

    def log_parser(self, log: str) -> dict[str, str]:
        return parse_log_phpunit_testdox(log)


@dataclass
class Carbon72ee09e5(PhpProfile):
    owner: str = "briannesbitt"
    repo: str = "Carbon"
    commit: str = "72ee09e5ada27bd82d668ba30e877722251d8322"

    @property
    def dockerfile(self):
        return f"""FROM php:8.3
RUN apt-get update && \
    apt-get install -y git unzip libxml2-dev libonig-dev && \
    docker-php-ext-install mbstring xml dom && \
    apt-get -y autoclean && \
    rm -rf /var/lib/apt/lists/*
RUN curl -sS https://getcomposer.org/installer | php -- --install-dir=/usr/local/bin --filename=composer
RUN git clone https://github.com/{self.mirror_name} /{ENV_NAME}
WORKDIR /{ENV_NAME}
RUN composer install
"""

    def log_parser(self, log: str) -> dict[str, str]:
        return parse_log_phpunit_testdox(log)


@dataclass
class PHPMailera80b3777(PhpProfile):
    owner: str = "PHPMailer"
    repo: str = "PHPMailer"
    commit: str = "a80b3777e68939a8ca0c7c32b58fb87190499f54"

    @property
    def dockerfile(self):
        return f"""FROM php:8.3
RUN apt-get update && \
    apt-get install -y git unzip libxml2-dev libzip-dev libonig-dev && \
    docker-php-ext-install mbstring zip && \
    apt-get -y autoclean && \
    rm -rf /var/lib/apt/lists/*
RUN curl -sS https://getcomposer.org/installer | php -- --install-dir=/usr/local/bin --filename=composer
RUN git clone https://github.com/{self.mirror_name} /{ENV_NAME}
WORKDIR /{ENV_NAME}
RUN composer install
"""

    def log_parser(self, log: str) -> dict[str, str]:
        return parse_log_phpunit_testdox(log)


# Register all PHP profiles with the global registry
for name, obj in list(globals().items()):
    if (
        isinstance(obj, type)
        and issubclass(obj, PhpProfile)
        and obj.__name__ != "PhpProfile"
    ):
        registry.register_profile(obj)
