var RACES;
var MAP_CENTER = { lat: 51.745909, lng: -1.243 };
var GPS_ACTIVITY = [];
var GPS_FIT = [];
var OLDEST_ACTIVITY;
var CURRENT_ACTIVITY = undefined;

function display_fit(data) {
    console.log("display_fit");

    CURRENT_ACTIVITY = data;
    // .id = data.activity_id;
    // CURRENT_ACTIVITY.description = data.description;

    // Title
    var title = "";
    if (data.activity_id != null) {
        title = title + " <a href='http://www.strava.com/activities/" + String(data.activity_id) + "'>" + data.activity_name + "</a>";
        title = title + " <button type='button' class='btn btn-warning' onClick='showUpdateDescription();' id='update-description'>Add splits to activity description</button>"
    } else {
        title = data.activity_name;
    }
    $("#activity-title").html(title);

    // Races select box
    var races_select = $("select#race");
    races_select.children('option').remove();
    data.races.forEach(function(race) {
        races_select.append('<option value=' + race.display_name + '>' + race.display_name + '</option>');
    });

    RACES = data.races;

    // Set selected race
    races_select.val(data.race.display_name)
        // Update distance and lap length fields
    race_changed(races_select, true);

    // map
    console.log(data.activity_centre);
    MAP_CENTER = data.activity_centre; //  { lat: 52.4558507, lng: -1.9242808 };
    GPS_ACTIVITY = []
    data.activity_latlng.forEach(function(item) {
        GPS_ACTIVITY.push({ lat: item[0], lng: item[1] });
    });

    GPS_FIT = [];
    data.fit_latlng.forEach(function(item) {
        GPS_FIT.push({ lat: item[0], lng: item[1] });
    });

    update_splits(data);

    initMap();
    // console.log(data.distance_time)
    // makeDistancePlot(data.distance_time);
    makeAnglePlot(data.angle_bins_freqs, data.accepted_angles_limits);

    $("#main-jumbo").toggle(true);


}

function update_splits(data) {
    // data should have properties: splits, fitError
    // Splits table
    CURRENT_ACTIVITY.splits = data.splits;
    var splits_table = $("#splits-table");
    var splits_distances = [];
    splits_table.children("tr").remove();
    data.splits.forEach(function(split) {
        splits_table.append("<tr><td>" + split.distance + "</td><td>" + split.total_mins + ":" + split.total_secs + "</td><td>" + split.split_mins + ":" + split.split_secs + "</td></tr>")
        splits_distances.push(split.distance);
    });

    $("#split-distances").val(splits_distances.join(", "));

    // Fit error
    var eqn = "$$ \\begin{eqnarray} \\epsilon = \\frac{1}{N} \\sum_{i} \\| \\mathbf{x}_{GPS, i} - \\mathbf{x}_{track, i} \\| \\nonumber \\\\";
    eqn = eqn + " = \\pm " + data.fitError.distance + " \\text{ m } \\implies \\pm " + data.fitError.time + " \\text{ s} \\nonumber  \\end{eqnarray}   $$"
    $("#fit-equation").html(eqn);
    var math = document.getElementById("fit-equation");
    MathJax.Hub.Queue(["Typeset", MathJax.Hub, math]);

    $("#avgSpeedMS").html(data.fitError.speed);
    $("#avgSpeedMPH").html(data.fitError.speedMPH);
}

function show_loading(el, loadingID) {

    $(el).hide();
    $("#" + loadingID).show();

}



function update_splits_table() {
    lap_length = $('#lap-length').val();
    race = $('#race option:selected').text();
    start_loc = $('#start-location').val();
    splits = $('#split-distances').val();
    lap_index = $('#lap-index option:selected').val();

    splits = splits.replace(/ /g, ',')
    splits = splits.replace(/,,/g, ',')

    console.log('lap length: ' + (lap_length)); // sanity check
    console.log('race distance: ' + (race));
    console.log('start location: ' + (start_loc));
    console.log('splits: ' + splits);

    $("#loading").show();

    $('#fitting-notification').hide();

    // Do ajax to retrieve new splits
    $.ajax({
        type: 'POST',
        url: '/splits',
        contentType: 'application/json',
        data: JSON.stringify({
            "lap_length": lap_length,
            "race": race,
            "splits": splits
        }),
        success: function(data) {
            if (data["error"]) {
                alert(data["error"]);
            } else {
                console.log(data);
                update_splits(JSON.parse(JSON.stringify(data)));
            }
        }
    });
    $("#loading").hide();
}

function saveDescription() {
    $("#descriptionModal").modal('hide');
    $.ajax({
        type: 'POST',
        url: '/update_description',
        contentType: 'application/json',
        data: JSON.stringify({
            "description": $("#descriptionText").val(),
            "activity_id": CURRENT_ACTIVITY.activity_id,
        }),
        success: function(data) {
            if (data["error"]) {
                alert(data["error"]);
            } else {
                console.log(data);
            }
        }
    });
}



function makeLapLengthDistanceEditable() {
    $('#lap-length').removeAttr('disabled');
    $('#race-dist').removeAttr('disabled');

}

// Code to update lap distance and starting position when race is changed
function race_changed(element, override_checkbox) {

    var selectedRace = $(element).find(":selected").text();
    console.log("Selected race: " + selectedRace);

    if ($('#auto-update-races').is(':checked') || override_checkbox) {
        const race = RACES.find(element => element.display_name == selectedRace);
        $('#lap-length').val(race.lap_length);
        $('#race-dist').val(race.distance);
        update_splits_options(race.lap_length);
    } else {
        console.log('Not auto updating race start and lap length');
    }

}

function update_splits_options(interval) {
    const race = RACES.find(element => element.display_name == $('#race option:selected').val());
    console.log('update_splits_options, race: ' + race);
    $('#split-distances').val(make_standard_splits(race, interval).join(', '));
}

function make_standard_splits(race, interval, start_at_finish) {
    if (start_at_finish == undefined) { start_at_finish = true; }

    split_distances = [];

    if (start_at_finish) {
        var lap = 0;
        while (race.distance - lap * interval > 0) {
            split_distances.push(race.distance - lap * interval);
            lap = lap + 1;
        }

        if (split_distances[split_distances - 1] != 0) {
            split_distances.push(0);
        }

        split_distances.sort((a, b) => a - b);

    } else {


        var lap = 1;

        while (lap * interval <= race.distance) {
            split_distances.push(lap * interval);
            lap = lap + 1;
        }

        console.log(split_distances[-1]);
        console.log(race.distance);
        if (split_distances[split_distances.length - 1] < race.distance) {
            split_distances.push(race.distance);
        }
    }

    return split_distances;
}

function loadActivities(before, after) {

    console.log("Load activities: " + String(before) + "-" + String(after));

    $("#activityLoading").show();
    $("#activityList").children("li").remove();

    $.ajax({
        type: 'GET',
        url: '/activities/' + String(before) + '/' + String(after),
        success: function(data) {
            if (data["error"]) {
                alert(data["error"]);
            } else {
                console.log(data);

                data = JSON.parse(JSON.stringify(data));

                var list = $("#activityList");
                data.activities.forEach(function(activity) {
                    var date = new Date(activity.date * 1000.0);
                    var dateStr = date.getDate() + "/" + String(Number(date.getMonth()) + 1) + "/" + date.getFullYear();
                    var classes = activity.isRace ? "race" : "non-race";
                    list.append("<li><a href='#' class='activity-item " + classes + "' onClick='selectActivity(" + activity.id + ")'>" + activity.name + " (" + dateStr + ")</a></li>");
                });

                OLDEST_ACTIVITY = data.activities[data.activities.length - 1].date;

                $("#loadOlderActivities").toggle(true);
            }
            $("#activityLoading").hide();
        }
    });
}

function loadOlder() {
    loadActivities(OLDEST_ACTIVITY, 0);
}

function loadDate() {
    var date = $("#activityDateSelector").val();
    var before = new Date(date);
    console.log(before);

    // Add three days
    before.setDate(before.getDate() + 3);

    var after = new Date(date);

    // Add three days
    after.setDate(after.getDate() - 3);

    console.log(before);
    console.log(after);


    loadActivities(before / 1000.0, after / 1000.0);
}

function selectActivity(id, page_load) {
    $("#stravaURL").val(id);
    loadStravaActivity(page_load);
    $('#activitySearchModal').modal('hide');
}

function loadStravaActivity(is_page_load) {
    $("#loading").toggle(true);

    $.ajax({
        type: 'POST',
        url: '/activity',
        contentType: 'application/json',
        data: JSON.stringify({ "url": $("#stravaURL").val() }),
        success: function(data) {
            console.log('Success!');

            if (data["error"]) {
                if (is_page_load != true) {
                    alert(data["error"]);
                }
            } else if (data["authorize_url"]) {
                $("#authorizeContent").html("<a href='" + data["authorize_url"] + "'>Authorize Strava to continue</a>");
                $('#authorizeModal').modal('toggle')
            } else {
                console.log(data);
                display_fit(JSON.parse(JSON.stringify(data)));
                parent.location.hash = data.activity_id;
            }
            $("#loading").toggle(false);
        }
    });
}

function showUpdateDescription() {
    console.log("Update description");
    $('#descriptionModal').modal('show');
    var description = CURRENT_ACTIVITY.description;

    description += "\n\nSplits from http://tracksplits2.herokuapp.com/#" + String(CURRENT_ACTIVITY.activity_id) + "\n";

    splits_list = [];
    CURRENT_ACTIVITY.splits.forEach(function(split) {
        if (Number(split.split_mins) < 2) {
            var timeInSecs = Number(split.split_mins) * 60 + Number(split.split_secs);
            splits_list.push(String(timeInSecs));
        } else {
            splits_list.push(split.split_mins + ":" + split.split_secs);
        }
    });

    description += splits_list.join(", ")


    $("#descriptionText").val(description);
}

$(document).ready(function() {

    if (parent.location.hash != "") {
        var activity_id = parent.location.hash.replace("#", "");
        console.log(activity_id);
        if (String(Number(activity_id)) == activity_id) {
            selectActivity(activity_id, true);
        }

    }

    // $("#update-description").click(function() {

    // });

    $("#stravaActivitySearch").click(function() {

        // Load activities if not already done
        if ($("#activityList").children("li").length == 0) {

            // Pass current timestamp in seconds
            loadActivities(Math.floor(Date.now() / 1000), 0);
        }
        $('#activitySearchModal').modal('toggle');

    })

    $("#about").click(function() {
        $('#aboutModal').modal('toggle');
    })

    $("#stravaRetrieve").click(function() {
        loadStravaActivity();
    });

    $("#loadActivity").click(function() {
        $("#loading").show();
        var form_data = new FormData($('#upload-file')[0]);
        $.ajax({
            type: 'POST',
            url: '/upload',
            data: form_data,
            contentType: false,
            cache: false,
            processData: false,
            success: function(data) {
                console.log('Success!');
                console.log(data);

                if (data["error"]) {
                    alert(data["error"]);
                } else {
                    console.log(data);
                    display_fit(JSON.parse(JSON.stringify(data)));
                    parent.location.hash = "";
                    $("#stravaURL").val("");

                }
                $("#loading").hide();
            },
        });
    });
});



function initMap() {
    var map = new google.maps.Map(document.getElementById('map'), {
        zoom: 18, // seems about right for an athletics track
        center: MAP_CENTER,
        mapTypeId: 'satellite'
    });
    map.setTilt(0); // don't tilt the map

    var activity_trace = new google.maps.Polyline({
        path: GPS_ACTIVITY,
        geodesic: true,
        strokeColor: '#FF0000',
        strokeOpacity: 0.5,
        strokeWeight: 2
    });
    //
    var fit_trace = new google.maps.Polyline({
        path: GPS_FIT,
        geodesic: true,
        strokeColor: '#1200ba',
        strokeOpacity: 1.0,
        strokeWeight: 2
    });

    activity_trace.setMap(map);
    fit_trace.setMap(map);

    var legend = document.getElementById('legend');
    console.log(legend);

    if (legend != undefined) {

        var div = document.createElement('div');
        div.innerHTML = 'GPS data';
        div.id = 'GPS-legend';
        legend.appendChild(div);

        var div2 = document.createElement('div');
        div2.innerHTML = 'Track fit';
        div2.id = 'fit-legend';
        legend.appendChild(div2);
        map.controls[google.maps.ControlPosition.LEFT_BOTTOM].push(legend);
    }

}


// For the file upload selector
$(function() {
    document.querySelector('.custom-file-input').addEventListener('change', function(e) {
        var fileName = document.getElementById("file").files[0].name;
        var nextSibling = e.target.nextElementSibling

        var fileWidth = nextSibling.getBoundingClientRect().width;
        console.log('File input width: ' + String(fileWidth));
        var maxLength = (fileWidth - 80.0) / 8.0; // 25;
        if (fileName.length > maxLength) {
            fileName = fileName.substring(0, maxLength) + '...';
        }
        nextSibling.innerText = fileName
    })
});



/*
Extra plots
*/
function hcLabelRender() {
    var s = this.name;
    var r = "";
    var lastAppended = 0;
    var lastSpace = -1;
    for (var i = 0; i < s.length; i++) {
        if (s.charAt(i) == ' ') lastSpace = i;
        if (i - lastAppended > 20) {
            if (lastSpace == -1) lastSpace = i;
            r += s.substring(lastAppended, lastSpace);
            lastAppended = lastSpace;
            lastSpace = -1;
            r += "<br>";
        }
    }
    r += s.substring(lastAppended, s.length);
    return r;
}

function makeAnglePlot(angles, angle_ranges) {

    plot_bands = [];
    angle_ranges.forEach(function(angle_range) {
        plot_bands.push({
            color: 'rgba(255,0,0,0.5)',
            opacity: 0.3,
            from: angle_range[0], // Start of the plot band
            to: angle_range[1] // End of the plot band
        });
    });

    Highcharts.chart('angle-plot', {

        chart: {
            type: 'areaspline',
            zoomType: 'x',
            panning: true,
            panKey: 'shift'
        },


        title: {
            text: 'Track orientation calculation'
        },

        xAxis: [{
            title: {
                text: 'Angle (radians)'
            },
            min: -1.5,
            max: 1.5,
            plotBands: plot_bands,
        }, ],

        yAxis: [{
            title: {
                text: 'Frequency'
            }
        }, ],

        legend: {
            layout: 'vertical',
            align: 'center',
            verticalAlign: 'bottom',
            labelFormatter: hcLabelRender
        },

        plotOptions: {
            spline: {
                marker: {
                    enabled: false
                }
            }
        },

        tooltip: {
            shared: true,
        },

        series: [{
            data: angles,
            name: 'Angles',
            type: 'spline',
            visible: true,
            marker: {
                radius: 1.5
            },
            showInLegend: true

        }, {
            type: 'area',
            name: 'Angles used to determine track orientation',
            data: [],
            showInLegend: true,
            visible: true,
            color: 'rgba(255,0,0,0.5)', // to match the plotband
        }, ],

    });
}

function makeDistancePlot(distances, speeds) {
    Highcharts.chart('distance-plot', {

        chart: {
            type: 'areaspline',
            zoomType: 'x',
            panning: true,
            panKey: 'shift'
        },

        title: {
            text: 'Calculated race progress'
        },

        yAxis: [{
            title: {
                text: 'Distance (metres)'
            },
            min: 0
        }, {
            opposite: true,
            title: {
                text: 'Speed (m/s)'
            },

        }],

        xAxis: {
            type: 'datetime',
            dateTimeLabelFormats: { // don't display the dummy year
                millisecond: '%M:%S',
                second: '%M:%S',
                minute: '%M:%S',
                hour: '%M:%S',
                day: '%M:%S',
                week: '%M:%S',
                month: '%M:%S',
                year: '%M:%S'
            },
            title: {
                text: 'Time (mm:ss)'
            }
        },
        legend: {
            layout: 'vertical',
            align: 'center',
            verticalAlign: 'bottom'
        },

        plotOptions: {
            spline: {
                marker: {
                    enabled: false
                }
            }
        },

        tooltip: {
            shared: true,
            xDateFormat: '%M:%S'
        },

        series: [{
            name: 'Distance (m)',
            showInLegend: true,
            lineWidth: 3,
            type: 'areaspline',
            fillOpacity: 0.3,
            data: distances,
        }, {
            name: 'Speed (m/s)',
            showInLegend: true,
            lineWidth: 2,
            yAxis: 1,
            fillOpacity: 0.0,
            type: 'spline',
            // For data, take every 4 points to make curve a little smoother
            data: speeds,
        }],


    });
}