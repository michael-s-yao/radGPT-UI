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

from main import hash_uid


@click.command()
@click.option(
    "-u", "--email", required=True, type=str, help="User email."
)
@click.option(
    "--seed/--uid", "is_seed", default=False, help="Return seed or UID."
)
def main(email: str, is_seed: bool = False):
    """Converts an input email address into a UUID."""
    seed = sum([ord(c) for c in email.lower()])
    rng = random.Random()
    rng.seed(seed)
    salt = str(uuid.UUID(int=rng.getrandbits(128), version=4))
    email = salt + email.lower()
    uid = hashlib.sha512(email.encode("utf-8")).hexdigest()
    if not is_seed:
        click.echo(uid)
        return
    click.echo(hash_uid(uid))


if __name__ == "__main__":
    main()
