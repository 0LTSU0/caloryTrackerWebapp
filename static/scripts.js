
var usernameAvailabilityCheckInProgress = false;

$( document ).ready(function() {
    
    if (location.href.endsWith("register"))
    {
        $("#username").on('change', function(){
            if (usernameAvailabilityCheckInProgress)
            {
                console.debug("Previous usernameAvailabilityCheckInProgress")
                return;
            }
            usernameAvailabilityCheckInProgress = true;
            $.getJSON( "/check_username_taken/" + $("#username").val(), function(res) {
                console.debug( "check_username_taken success! Response", res );
                usernameAvailabilityCheckInProgress = false;
                if (res)
                {
                    $("#username").css("color", "crimson");
                    $("#usernameTakenError").show();
                    $("#registerButt").attr("disabled", true);
                }
                else {
                    $("#username").css("color", "");
                    $("#usernameTakenError").hide();
                    $("#registerButt").removeAttr("disabled");
                }
            })
        });
        $("#username").on('input', function(){
            $("#error_msg_from_flask").hide() 
        });
        $("#password").on('input', function(){
            $("#error_msg_from_flask").hide() 
        });
        $("#repassword").on('input', function(){
            $("#error_msg_from_flask").hide() 
            if ($("#repassword").val() != $("#password").val())
            {
                $("#repassword").css("color", "crimson");
                $("#password").css("color", "crimson");
                $("#passwordsDontMatchError").show();
                $("#registerButt").attr("disabled", true);
            } else {
                $("#repassword").css("color", "");
                $("#password").css("color", "");
                $("#passwordsDontMatchError").hide();
                $("#registerButt").removeAttr("disabled");
            }
        }); 
    }
});