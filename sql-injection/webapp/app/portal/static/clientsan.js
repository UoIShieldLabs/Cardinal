/* Cardinal — CLIENT-SIDE sanitization (the "sanitized" version of the app).
 *
 * Loaded on every page only when ?sanitize=on. Three DIFFERENT TYPES of
 * client-side defense, assigned to inputs/forms via data-san attributes in the
 * templates, so one app demonstrates all three across every input area:
 *
 *   data-san="regex"     (on a <form>)  Type 1 - JS regex DENYLIST on submit.
 *   data-san="keystroke" (on a field)   Type 3 - strip disallowed chars as typed.
 *   (HTML5 pattern/maxlength attributes) Type 2 - native, needs no JS.
 *
 * Every one of these runs in the browser, so every one is defeated by sending
 * the request directly (curl/Burp) -- the server does no filtering. The point is
 * the LOCATION, not the technique.
 */
(function () {
  var DENY = /['";]|--|#|\/\*|\b(union|select|insert|update|delete|drop|or|and|sleep)\b/i;
  var OKCHAR = /[A-Za-z0-9 ]/;

  function flash(form, msg) {
    var box = form.querySelector(".clientsan-err");
    if (!box) {
      box = document.createElement("div");
      box.className = "clientsan-err flash err";
      box.style.marginTop = "10px";
      form.appendChild(box);
    }
    box.textContent = msg;
    box.style.display = "block";
  }

  document.addEventListener("DOMContentLoaded", function () {
    // Type 1 - regex denylist, validated on submit.
    document.querySelectorAll('form[data-san="regex"]').forEach(function (form) {
      form.addEventListener("submit", function (e) {
        var fields = form.querySelectorAll("input, textarea");
        for (var i = 0; i < fields.length; i++) {
          if (fields[i].value && DENY.test(fields[i].value)) {
            e.preventDefault();
            flash(form, "Blocked by client-side sanitization (regex denylist).");
            return;
          }
        }
      });
    });

    // Type 3 - real-time keystroke filtering (also fires on paste).
    document.querySelectorAll('[data-san="keystroke"]').forEach(function (f) {
      f.addEventListener("input", function () {
        var cleaned = f.value.split("").filter(function (c) {
          return OKCHAR.test(c);
        }).join("");
        if (cleaned !== f.value) f.value = cleaned;
      });
    });
  });
})();
