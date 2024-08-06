#!/usr/bin/env python3
"""
Flask app for human-user studies.

Author(s):
    Michael Yao @michael-s-yao
    Allison Chae @allisonjchae

Licensed under the MIT License. Copyright University of Pennsylvania 2024.
"""
import hashlib
import json
import jsonlines
import numpy as np
import os
import re
import requests
from collections import defaultdict
from datetime import datetime
from flask import Flask, abort, render_template, redirect, request, url_for
from pathlib import Path
from typing import Any, Dict, Sequence, Optional, Union
from urllib.parse import quote_plus


def read_imaging_studies(
    fn: Union[Path, str] = os.path.join(
        os.path.dirname(__file__), "static", "assets", "studies.txt"
    )
) -> Sequence[str]:
    """
    Imports the space of valid imaging studies to choose from.
    Input:
        fn: the path to the file containing the listed imaging studies.
    Returns:
        A list of the valid imagng studies to choose from.
    """
    assert os.path.isfile(fn)
    with open(fn, "r") as f:
        return [study.strip() for study in f.readlines()] + ["None"]


def add_alternate_matches(
    studies: Sequence[str], sep_token: str = "<|***|>"
) -> Sequence[str]:
    """
    Appends alternate search matches for the input imaging studies.
    Input:
        studies: a list of the input imaging studies.
        sep_token: the token to separate the input match strings.
    Returns:
        A list of the studies with their appended alternative search matches.
    """
    def add_alts(study: str) -> str:
        if "radiograph" in study.lower():
            study += sep_token + "X-ray" + sep_token + "X ray"
        if "radiograph" in study.lower() and "chest" in study.lower():
            study += sep_token + "CXR"
            study += sep_token + "Chest X-ray" + sep_token + "Chest X ray"
        if "mri" in study.lower():
            study += "Magnetic Resonance Imaging"
        if "ct" in study.lower():
            study += "Computed Tomography"
        return study

    return list(map(add_alts, studies))


def read_patient_cases(
    fn: Union[Path, str] = os.path.join(
        os.path.dirname(__file__), "static", "assets", "cases.jsonl"
    )
) -> Sequence[str]:
    """
    Imports the patient cases to evaluate.
    Input:
        fn: the path to the file containing the patient cases.
    Returns:
        A list of the patient cases to evaluate.
    """
    assert os.path.isfile(fn)
    with open(fn, "r") as f:
        with jsonlines.Reader(f) as reader:
            return list(reader)


def read_guidelines(
    fn: Union[Path, str] = os.path.join(
        os.path.dirname(__file__), "static", "assets", "guidelines.jsonl"
    )
) -> Sequence[Dict[str, Any]]:
    """
    Reads the ACR Appropriateness Criteria guidelines.
    Input:
        fn: the path to the file containing the imaging guidelines.
    Returns:
        A list of the guideline objects.
    """
    with open(fn, "r") as f:
        with jsonlines.Reader(f) as reader:
            return list(reader)


def hash_uid(uid: str) -> int:
    """
    Returns a determinstic integer from a string.
    Input:
        uid: an input string.
    Returns:
        A deterministic integer seed generated from the string.
    """
    return int(hashlib.sha256(uid.encode("utf-8")).hexdigest(), 16) % (10 ** 8)


def create_app(debug: bool = False) -> Flask:
    """
    Creates the Python Flask app with the relevant endpoints.
    Input:
        debug: whether the function is run in the development environment.
    Returns:
        The Python Flask app instantiation with the relevant endpoints.
    """
    app = Flask(
        __name__,
        instance_relative_config=True,
        template_folder=os.path.join(os.path.dirname(__file__), "templates")
    )

    @app.route("/", methods=["GET"])
    def index():
        uid = request.args.get("uid", None)
        if uid is None:
            return render_template("instructions.html")
        seed = hash_uid(uid)

        cases = read_patient_cases(
            os.path.join(
                os.path.dirname(__file__),
                "static",
                "assets",
                "demo.jsonl" if debug else "cases.jsonl"
            )
        )
        questions = list(map(lambda data: data["case"], cases))
        topics = list(map(lambda data: data["topics"], cases))

        category_to_format = defaultdict(lambda: "gray")
        category_to_format.update({
            "Usually appropriate": "green",
            "May be appropriate": "yellow",
            "Usually not appropriate": "red",
        })

        radiation = u"\u2622 "
        guidelines = {
            data["Topic"]: [
                {
                    "Procedure": study["Procedure"],
                    "Radiation": (
                        radiation * int(study["Adult RRL"])
                        if int(study["Adult RRL"]) > 0
                        else "None"
                    ),
                    "Category": category_to_format[
                        study["Appropriateness Category"]
                    ]
                }
                for study in data["Scenarios"][0]["Studies"]
            ]
            for data in read_guidelines()
        }
        guidelines = [
            [{"Topic": t, "Table": guidelines[t]} for t in topic_list]
            for topic_list in topics
        ]

        rng = np.random.default_rng(seed=seed)
        with_guidance = rng.choice(
            len(questions), size=(len(questions) // 2), replace=False
        )
        show_guidance = [
            qidx in with_guidance for qidx in np.arange(len(questions))
        ]

        rng = np.random.default_rng(seed=seed)
        sort_idxs = rng.choice(
            len(questions), size=len(questions), replace=False
        )

        rng = np.random.default_rng(seed=seed)
        timed = str(rng.choice(2, size=1, replace=False)[0])

        questions = [questions[idx] for idx in sort_idxs]
        guidelines = [guidelines[idx] for idx in sort_idxs]
        show_guidance = [show_guidance[idx] for idx in sort_idxs]
        show_guidance_str = "".join([str(int(b)) for b in show_guidance])
        sort_idxs = ",".join([str(idx) for idx in sort_idxs])
        options_pretty = read_imaging_studies()
        options = add_alternate_matches(options_pretty)

        return render_template(
            "index.html",
            options=options,
            options_pretty=options_pretty,
            questions=questions,
            guidelines=guidelines,
            show_guidance=show_guidance,
            show_guidance_str=show_guidance_str,
            uid=uid,
            seed=str(seed),
            sort_idxs=sort_idxs,
            timed=timed,
            zip=zip
        )

    @app.route("/success", methods=["GET"])
    def success():
        return render_template("success.html")

    @app.route("/error", methods=["GET"])
    @app.route("/error/<err_type>", methods=["GET"])
    def error(err_type: Optional[str] = ""):
        return render_template("error.html", err_type=err_type)

    @app.route("/api/v1/submit", methods=["POST"])
    def write_answers():
        if len(request.form.get("name", "")):
            abort(500)
        uid = request.form.get("uid", "None")
        studies = read_imaging_studies()
        response = []

        prog = re.compile(r"Q\d+")
        qas = [(q, a) for q, a in request.form.items()]
        qas = list(
            filter(qas, key=lambda _qa: prog.fullmatch(_qa[0]) is not None)
        )
        answers = list(map(lambda _qa: _qa[-1], qas))
        aidxs = []
        for a in answers:
            try:
                aidxs.append(str(studies.index(a)))
            except ValueError:
                aidxs.append("-1")

        qidxs = request.form.get("sort_idxs", "None")
        qidxs = qidxs.replace("[", "").replace("]", "").split(",")

        with_guidance = list(request.form.get("with_guidance", ""))

        response = [
            f"Q{qi},A{ai},{b}"
            for qi, ai, b in zip(qidxs, aidxs, with_guidance)
        ]

        time = datetime.now().astimezone().replace(microsecond=0).isoformat()
        is_timed = request.form.get("timed", "None")
        seed = request.form.get("seed", "None")
        duration = request.form.get("duration", "None")

        form_url = (
            "https://docs.google.com/forms/d/e/"
            "1FAIpQLSdjaP9_HApCZgCC9VaoPFMCMUIgJmXfRcC2Tb31jURG4NPxqQ/"
            "formResponse?&submit=Submit?usp=pp_url&entry.1566494565={user}&"
            "entry.1604544479={answer}&entry.921671925={time}&"
            "entry.2066832372={duration}&entry.734084621={is_timed}"
        )
        form_url = form_url.format(
            user=uid,
            answer=quote_plus(json.dumps(response)),
            time=quote_plus(time),
            is_timed=is_timed,
            duration=duration,
            seed=seed,
            with_guidance=with_guidance
        )
        try:
            response = requests.get(form_url)
        except requests.exceptions.ConnectionError:
            return redirect(url_for("error/connection"))
        if response.status_code == 200:
            return redirect(url_for("success"))
        return redirect(url_for("error/post"))

    app.jinja_env.filters["zip"] = zip

    return app


debug = False
app = create_app(debug=debug)
