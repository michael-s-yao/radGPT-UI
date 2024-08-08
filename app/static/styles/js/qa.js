function NonNull(item) {
  if (item === null || item === undefined)
    throw new Error();
  return item;
}

let studies = document.getElementById("imaging_studies");

function checkIfFinished() {
  const options = [...studies.options].map((opt) => opt.text);
  let isFinished = [...document.querySelectorAll(".question")]
    .every((x) => options.includes(x.querySelector("input").value));
  if (isFinished) {
    document.getElementById("submit").style.display = "block";
    window.onbeforeunload = null;
  } else {
    document.getElementById("submit").style.display = "none";
    window.onbeforeunload = function() {
      return true;
    };
  }
}

function linkDatalist(question) {
  let input = NonNull(question.querySelector("input"));
  input.onfocus = function () {
    studies.style.display = "block";
    input.style.borderRadius = "8px 8px 0 0";
  };

  document.getElementsByTagName("body")[0].onclick = function(e) {
    if (
      (e.target instanceof HTMLInputElement) ||
      (e.target instanceof HTMLOptionElement) ||
      (e.target instanceof HTMLButtonElement)
    )
      return;
    studies.style.display = "none";
    input.style.borderRadius = "8px";
    input.style.borderColor = null;
  }

  for (let option of studies.options) {
    option.onclick = function (e) {
      input.value = option.text;
      studies.style.display = "none";
      input.style.borderRadius = "8px";
      input.style.borderColor = null;
    }
  };

  input.oninput = function() {
    currentFocus = -1;
    input.style.borderColor = null;
    var text = input.value.toUpperCase();
    for (let option of studies.options) {
      if (option.value.toUpperCase().indexOf(text) > -1)
        option.style.display = "block";
      else
        option.style.display = "none";
    };
  };

  input.onkeydown = function(e) {
    input.style.borderColor = null;
    if (e.keyCode == 40) {
      currentFocus++;
      addActive(studies.options);
    } else if (e.keyCode == 38) {
      currentFocus--;
      addActive(studies.options);
    } else if (e.keyCode == 13) {
      e.preventDefault();
    if (currentFocus > -1 && studies.options)
      studies.options[currentFocus].click();
    }
  }

  input.onkeyup = checkIfFinished;
};

function unlinkDatalist() {
  [...document.querySelectorAll(".question")]
    .map(function (input) {
      input.onfocus = null;
      [...studies.options].map(function (option) { option.onclick = null; });
      input.oninput = null;
      input.onkeydown = null;
      input.onkeyup = null;
      input.style.borderColor = null;
    });

  for (let option of studies.options)
    option.style.display = "block";
};

function addActive(x) {
  if (!x)
    return false;
  removeActive(x);
  if (currentFocus >= x.length)
    currentFocus = 0;
  if (currentFocus < 0)
    currentFocus = (x.length - 1);
  x[currentFocus].classList.add("active");
}

function removeActive(x) {
  for (var i = 0; i < x.length; i++)
    x[i].classList.remove("active");
}

function validateInput(event) {
  const options = [...studies.options]
    .filter((x) => x.text.length > 0)
    .map((x) => x.text.substring(0, x.text.length));
  const activeElement = NonNull(document.querySelector(".question.active"));
  const input = NonNull(activeElement.querySelector("input"));
  const isValid = options.includes(input.value);
  if (((input.value.length === 0) || (isValid)) && (event.target.id.toLowerCase() === "back")) {
    activeView = Math.max(activeView - 1, 1);
    setView(activeView);
    for (let option of studies.options)
      option.style.display = "block";
  } else if ((isValid) && (event.target.id.toLowerCase() == "next")) {
    activeView = Math.min(activeView + 1, numQuestions);
    setView(activeView);
    for (let option of studies.options)
      option.style.display = "block";
  } else {
    input.style.borderColor = "var(--red)"; 
  }
}

function resetView() {
  [...document.querySelectorAll(".question")]
    .map((x) => x.classList.remove("active"));
  [...document.querySelectorAll("button.nav")]
    .map((x) => x.style.display = null);
  unlinkDatalist();
  [...document.querySelectorAll("details")]
    .map((x) => x.style.display = "none");
  document.querySelector("#acr-info-block").classList.remove("active");
}

function setView(idx) {
  resetView();
  let view = [...document.querySelectorAll(".question")]
    .find((x) => x.id === "Q" + idx.toString() + "-box");
  NonNull(view).classList.add("active");
  linkDatalist(NonNull(view));
  const re = new RegExp(String.raw`guidelines-Q${idx}-T\d`, "g");
  let recs = [...document.querySelectorAll("details")]
    .filter((x) => x.id.match(re))
    .map((x) => x.style.display = null);
  if (idx === 1)
    document.querySelector("button#back").style.display = "none";
  if (idx === numQuestions)
    document.querySelector("button#next").style.display = "none";
  const withGuidance = document.getElementById("with_guidance").value;
  if (withGuidance[idx - 1] === "1")
    document.querySelector("#acr-info-block").classList.add("active");
}

var activeView = 1;
var currentFocus = -1;
const numQuestions = document.querySelectorAll(".question").length;
setView(activeView);
[...document.querySelectorAll("button.nav")]
  .map((x) => x.addEventListener("click", validateInput));
document.addEventListener("click", checkIfFinished);
document.getElementById("submit").onclick = function() {
  return confirm("I confirm that I have completed this task to the best of my ability.");
};
window.onbeforeunload = function() {
  return true;
};

const interval = 1000;
const totalMinutes = 50;
var totalSteps = Math.round(totalMinutes * 60);
var expected = Date.now() + interval;
setTimeout(updateCountdown, interval);

function updateCountdown() {
  var dt = Date.now() - expected;
  if (dt > interval)
    expected += interval * Math.floor(dt / interval);

  if (document.getElementById("timed").value !== "0") {
    const hours = Math.floor((totalSteps % (3600 * 24)) / 3600);
    const minutes = Math.floor((totalSteps % (3600)) / 60);
    const seconds = Math.floor(totalSteps % 60);

    document.getElementById("hours").innerText = Math.max(hours, 0);
    document.getElementById("minutes").innerText = Math.max(minutes, 0);
    document.getElementById("seconds").innerText = Math.max(seconds, 0);
  }

  expected += interval;
  totalSteps = totalSteps - 1;
  document.getElementById("duration")
    .value = (Math.round(totalMinutes * 60) - totalSteps).toString();
  setTimeout(updateCountdown, Math.max(0, interval - dt));
}
