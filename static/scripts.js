
var usernameAvailabilityCheckInProgress = false;
const dates = ["Sunday", "Moday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]

function get_date_with_day_name(datestr)
{
    //from python we getr dates in DDMMYYYY
    let d = datestr.slice(0,2)
    let m = datestr.slice(2,4)
    let y = datestr.slice(4,9)
    let date = new Date(y + '-' + m + "-" + d)
    return dates[date.getDay()] + " " + d + "." + m + "." + y
}

function get_date_url(datestr, offset)
{
    let d = datestr.slice(0,2)
    let m = datestr.slice(2,4)
    let y = datestr.slice(4,9)
    let date = new Date(y + '-' + m + "-" + d)
    date.setDate(date.getDate() + offset)
    console.debug(offset, dates[date.getDay()])
    let new_d = date.getDate().toString().padStart(2, '0'); // Get the day and pad it to 2 digits
    let new_m = (date.getMonth() + 1).toString().padStart(2, '0'); // Get the month (getMonth() returns 0-based month, so +1)
    let new_y = date.getFullYear(); // Get the full year
    return new_d + new_m + new_y
}

function goto_url(id)
{
    window.location.href = $("#" + id).attr('href')
}

$( document ).ready(function() {
    if (location.href.includes("/foods/day"))
    {
        let datestr = location.href.slice(location.href.lastIndexOf("/") + 1)
        console.log("current date is", get_date_with_day_name(datestr))
        $("#headertext").text("Records for " + get_date_with_day_name(datestr))
        let prev_date_url = get_date_url(datestr, -1)
        let next_date_url = get_date_url(datestr, 1)
        $("#prev_date_button").attr('href', '/foods/day/'+prev_date_url);
        $("#next_date_button").attr('href', '/foods/day/'+next_date_url);
    }

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