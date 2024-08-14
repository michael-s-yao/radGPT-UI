"""
Simple script to convert an input email address into a UUID.

Author(s):
    Michael Yao @michael-s-yao
    Allison Chae @allisonjchae

Licensed under the MIT License. Copyright University of Pennsylvania 2024.
"""
import click
import hashlib
import random
import uuid


@click.command()
@click.option(
    "-u", "--email", required=True, type=str, help="User email."
)
def main(email: str):
    """Converts an input email address into a UUID."""
    seed = sum([ord(c) for c in email.lower()])
    rng = random.Random()
    rng.seed(seed)
    salt = str(uuid.UUID(int=rng.getrandbits(128), version=4))
    email = salt + email.lower()
    click.echo(hashlib.sha512(email.encode("utf-8")).hexdigest())


if __name__ == "__main__":
    main()
