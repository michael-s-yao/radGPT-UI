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
from flask import (
    Flask, abort, render_template, redirect, request, send_file, url_for
)
from pathlib import Path
from typing import Any, Dict, Sequence, Optional, Union
from urllib.parse import quote_plus


PGY_PARTICIPANTS = [
    "7fcf2f33990f1031ffa1b3b1a1af65ddd74d82c1ba2cb10b502b55d22a7d531c769a4b2f5f1555ddb781cee970b9200c25d969a6099d1842d3cc8317dc6877e3",
    "072ae74ae00365202734f5b8dd420d67fbbb636f14e4d7b024cd06b0573f713ddd90880d386a061e45c251062d7110c54ca8da09a01714a1a99bad20a7f5b635",
    "77f2092e7247d9664bddb96fccd115314ecb55fd05667bd5a5d981a3125a753af93ddbdb4ac9489604dbee4df94a2a928f75952d88f23f62641f0fd31a8dd780",
    "96e8f28c6c75a9ddf806dc55ef0f71df984e95c750d206b7649dfa5d9bc2a06084dd47437de5027e07be20d96815da32bedd86db71ab3d7aa8ddcf23ce7a5d03",
    "47333aaf4d3eba3e72c6773d3babc413ab6e1aecbd1a35b9cb415c44cc2246a5d60e6ab4f9c5a1b7344699187d9e627b9e9e777c4f13bf5bbe943534e08a56c0",
    "3506131688abd9bf086c20e14d9a4f27a420cbb624b8c9c85d8014f9a57748bf7ed43817959291fb6698d8af6458aad46fe43fd35b1e79f5aaece9d31f02c9b7",
    "cdda740ff28719614f6df6e0f2c9e70273ce359adbd557895e5b763f94b875ae5713c8b11bc0b060bc59a3db65c5704e437a0026ef17d1f0a338dd0dace545d8",
    "875e88de37a21b1a26850de1f1c5eb21dd8f3234f8be19e991d387b278b4cfae381533ab71f3cf6fc474ca178677e01d04a2e10b9a7d0a2ae9e6297ec6fe4878",
    "407377c6c6f7a3e78a58b4bbf38e879e0c24c3f011f59cf640b128e251ce45df8a2e74e63954a61258c4928bc3b758b6178f86599e00b6f309ce913feae14c9a",
]


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
        if "us" in study.lower():
            study += "Ultrasound"
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
            guidelines = list(reader)
    topics = [g["Topic"] for g in guidelines]
    try:
        idx = topics.index("Suspected Pulmonary Embolism")
        scenarios = guidelines[idx]["Scenarios"]
        scenario_names = [sc["Scenario"] for sc in scenarios]
        guidelines[idx]["Scenarios"] += [guidelines[idx]["Scenarios"][-2]]
        guidelines[idx]["Scenarios"] = guidelines[idx]["Scenarios"][::-1]
        return guidelines
    except ValueError:
        return guidelines


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
    @app.route("/<demo>", methods=["GET"])
    def index(demo: Optional[str] = ""):
        is_demo = demo is not None and (demo.lower() == "demo")
        uid = "demo" if is_demo else request.args.get("uid", None)
        if uid is None:
            return render_template("instructions.html")
        seed = hash_uid(uid)

        cases = read_patient_cases(
            os.path.join(
                os.path.dirname(__file__),
                "static",
                "assets",
                "demo.jsonl" if is_demo else "cases.jsonl"
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
        if is_demo:
            timed = "0"
        if uid in PGY_PARTICIPANTS:
            timed = "1"

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
        if uid.lower() == "demo":
            return redirect(url_for("success"))
        studies = read_imaging_studies()
        response = []

        prog = re.compile(r"Q\d+")
        qas = [(q, a) for q, a in request.form.items()]
        qas = list(
            filter(lambda _qa: prog.fullmatch(_qa[0]) is not None, qas)
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

    @app.route("/.well-known/pki-validation/<filename>")
    def dcv(filename):
        if filename == "F3D6BF31FA6C60FC741BD13F405FEB88.txt":
            return send_file("F3D6BF31FA6C60FC741BD13F405FEB88.txt")
        abort(500)

    return app


debug = False
app = create_app(debug=debug)
