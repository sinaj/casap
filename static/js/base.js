$(document).ready(function () {
    $(".alert.sys-msg").fadeTo(3000, 500).slideUp(500, function () {
        $(".alert.sys-msg").slideUp(500);
    });

    setup_timezone_offset();

});

var setup_timezone_offset = function () {
    setCookie("tz_offset", (new Date()).getTimezoneOffset());
    setCookie("tz_name", Intl.DateTimeFormat().resolvedOptions().timeZone);
}

function setCookie(name, value, exdays) {
    var d = new Date();
    d.setTime(d.getTime() + (exdays * 24 * 60 * 60 * 1000));
    var expires = "expires=" + d.toUTCString();
    if (exdays) {
        document.cookie = name + "=" + value + ";" + expires + ";path=/";
    }
    else {
        document.cookie = name + "=" + value + ";path=/";
    }
}

function getCookie(name) {
    var cookieValue = null;
    if (document.cookie && document.cookie != '') {
        var cookies = document.cookie.split(';');
        for (var i = 0; i < cookies.length; i++) {
            var cookie = jQuery.trim(cookies[i]);
            // Does this cookie string begin with the name we want?
            if (cookie.substring(0, name.length + 1) == (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}