
var usernameAvailabilityCheckInProgress = false;
const dates = ["Sunday", "Moday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"];
const editable_food_row = '<tr>'+
                          '<td epoch=__ToBeForced1__>__ToBeForced2__</td>'+
                          '<td><input type="text"/></td>'+
                          '<td><input type="number"/></td>'+
                          '<td><input type="text"/></td>'+
                          '<td><button class="btn btn-danger btn-sm" onclick="removeRowFromTable(this)">Delete</button></td>'+
                          '</tr>';
const editable_exercise_row = '<tr>'+
                              '<td epoch=__ToBeForced1__>__ToBeForced2__</td>'+
                              '<td><input type="number"/></td>'+
                              '<td><input type="text"/></td>'+
                              '<td><button class="btn btn-danger btn-sm" onclick="removeRowFromTable(this)">Delete</button></td>'+
                              '</tr>';
const colWithTime = 0;

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

function removeRowFromTable(button)
{
    let deleteRowNum = button.getAttribute("row_identifier");
    console.debug("row wanted to be deleted is", deleteRowNum);
    let table_name = button.parentElement.parentElement.parentElement.getAttribute("id")
    $("#" + table_name + " tr:nth-child(" + deleteRowNum + ")").remove();
}

function addNewRowToFoodTable()
{
    let currentEpoch = Math.round(new Date().getTime() / 1000).toString();
    let dateStr = epochToReadable(currentEpoch)
    let editable_food_row_w_time = editable_food_row.replace("__ToBeForced2__", dateStr);
    editable_food_row_w_time = editable_food_row_w_time.replace("__ToBeForced1__", currentEpoch);
    if ($('#food_table_body tr').length) {
        $('#food_table_body tr:last').after(editable_food_row_w_time);
    } else {
        $('#food_table_body').append(editable_food_row_w_time);
    }
    setRowNumbersToDeleteButtons("food_table_body");
}

function addNewRowToExerciseTable()
{
    let currentEpoch = Math.round(new Date().getTime() / 1000).toString();
    let dateStr = epochToReadable(currentEpoch)
    let editable_exrc_row_w_time = editable_exercise_row.replace("__ToBeForced2__", dateStr);
    editable_exrc_row_w_time = editable_exrc_row_w_time.replace("__ToBeForced1__", currentEpoch);
    if ($('#exercise_table_body tr').length) {
        $('#exercise_table_body tr:last').after(editable_exrc_row_w_time);
    } else {
        $('#exercise_table_body').append(editable_exrc_row_w_time);
    }
    setRowNumbersToDeleteButtons("exercise_table_body");
}

function setRowNumbersToDeleteButtons(tablebody)
{
    // this sets row_identifier attributes to the delete buttons inside the table so that its possible to know on which row is which button.
    // Needs to be called on page load AND whenever the number of rows inside the table changes!
    let ctr = 1;
    $(`#${tablebody} > tr > td`).each(function() {
        for (let child of this.childNodes)
        {
            if (child.tagName == "BUTTON")
            {
                child.setAttribute("row_identifier", ctr);
                ctr = ctr + 1;
            }
        }
    });
}

function postDataAndRedirect(url, data) {
    fetch(url, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify(data)
    })
    .then(response => {
        if (response.redirected) {
            window.location.href = response.url; // Fallback in case the auto-redirect doesn't work
        }
    })
    .catch(error => console.error('Error:', error));
}

function postFoodsAndExercisesDay()
{
    sendData = {};
    //Creates json of content inside the food table
    let data = [];
    let dataKeys = ["datetime", "food", "calories", "note"] // this corresponds to which column in the table contains what data
    $('#food_table_body tr').each(function(index, element) {
        console.debug(index, element);
        let dataEntry = {};
        ctr = 0
        $(this).find('td').each(function(){
            let cellElem = $(this);
            if (cellElem.find('button').length > 0){
                return; // skip delete (or possible future edit) button cells
            }
            if (cellElem.text()) //data in cells without user input boxes should be findable by this
            {
                if (ctr == colWithTime)
                {
                    dataEntry[dataKeys[ctr]] = cellElem.attr("epoch")
                } else {
                    dataEntry[dataKeys[ctr]] = cellElem.text()
                }
            } else if (cellElem.find('input').length > 0) {
                let inputElem = cellElem.find('input');
                dataEntry[dataKeys[ctr]] = inputElem.val()
            } else { //the cell must be empty
                dataEntry[dataKeys[ctr]] = "";
            }
            ctr++;
        })
        data.push(dataEntry);
    });
    sendData["foods"] = data;

    //Then create json of what is inside the exercise table
    data = [];
    dataKeys = ["datetime", "calories", "desc"] // this corresponds to which column in the table contains what data
    $('#exercise_table_body tr').each(function(index, element) {
        console.debug(index, element);
        let dataEntry = {};
        ctr = 0
        $(this).find('td').each(function(){
            let cellElem = $(this);
            if (cellElem.find('button').length > 0){
                return; // skip delete (or possible future edit) button cells
            }
            if (cellElem.text()) //data in cells without user input boxes should be findable by this
            {
                if (ctr == colWithTime)
                {
                    dataEntry[dataKeys[ctr]] = cellElem.attr("epoch")
                } else {
                    dataEntry[dataKeys[ctr]] = cellElem.text()
                }
            } else if (cellElem.find('input').length > 0) {
                let inputElem = cellElem.find('input');
                dataEntry[dataKeys[ctr]] = inputElem.val()
            } else { //the cell must be empty
                dataEntry[dataKeys[ctr]] = "";
            }
            ctr++;
        })
        data.push(dataEntry);
    });
    sendData["exercises"] = data;

    console.log("to be submitted", sendData, "to", window.location.href + "/post");
    postDataAndRedirect(window.location.href + "/post", sendData);
}

function epochToReadable(epochstr)
{
    console.debug(epochstr)
    let d = new Date( parseInt(epochstr) *1000);
    return d.toLocaleString()
}

function convertTableEpochs()
{
    $('#food_table_body tr').each(function() {
        $(this).find('td:first').each(function(){
            console.debug("convertTableEpochs", $(this).text())
            $(this).attr("epoch", $(this).text()) //store the original epoch string to attribute
            $(this).text(epochToReadable($(this).text()))
        })
    })
    $('#exercise_table_body tr').each(function() {
        $(this).find('td:first').each(function(){
            console.debug("convertTableEpochs", $(this).text())
            $(this).attr("epoch", $(this).text()) //store the original epoch string to attribute
            $(this).text(epochToReadable($(this).text()))
        })
    })
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
        setRowNumbersToDeleteButtons("food_table_body")
        setRowNumbersToDeleteButtons("exercise_table_body")
        convertTableEpochs()
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