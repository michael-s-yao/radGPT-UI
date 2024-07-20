function isAlphaNumeric(str) {
  var code, i, len;
  for (i = 0, len = str.length; i < len; i++) {
    code = str.charCodeAt(i);
    if (!(code > 47 && code < 58) && // numeric (0-9)
        !(code > 64 && code < 91) && // upper alpha (A-Z)
        !(code > 96 && code < 123)) { // lower alpha (a-z)
      return false;
    }
  }
  return true;
};

function toggleContinue() {
  const button = document.getElementById("continue");
  const consent = document.getElementById("consent");
  const uid = document.getElementById("uid").value;
  valid = consent.checked && isAlphaNumeric(uid) && uid.length === 512;
  if (valid) {
    button.classList.add("active");
    button.onclick = function () { window.location = "/?uid=" + uid };
  } else {
    button.classList.remove("active");
    button.onclick = null;
  }
};
