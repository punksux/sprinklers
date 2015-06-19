$('.manButt').on('click', function () {
    manual($(this).attr('id'));
    getUptimeCount();
});

function manual(number) {
    var length = $("#man" + number).val();
    if (length === '') length = '0';
    $.ajax(
        {
            type: 'post',
            url: "/manual",
            data: {
                'number': number,
                'length': length
            }
        }
    )
        .done(function (data) {
            showMessages(data.message);
            var man;
            if (data.onOff === 'on') {
                $('#onOff' + number).switchClass('off', 'on');
                $('#' + number).addClass('manOff').children().html('Manual Off');
                if (parseInt(length) > 0) {
                    man = setTimeout(function () {
                        $('#onOff' + number).switchClass('on', 'off');
                        $('#' + number).removeClass('manOff').children().html('Manual On');
                    }, (parseInt(length) * 1000) * 60);
                }
            } else {
                $('#onOff' + number).switchClass('on', 'off');
                $('#' + number).removeClass('manOff').children().html('Manual On');
                clearTimeout(man)
            }
        })
}

$('#applyButton').click(function(){
    apply();
    getUptimeCount();
});

function apply() {
    var days = $('#days').val();
    var ttime = $('#ttime').val();
    var amPM = $('input[name="amPM"]:checked').val();
    var zone1length = $('#zone1length').val();
    var zone2length = $('#zone2length').val();
    var zone3length = $('#zone3length').val();
    $.ajax(
        {
            type: 'post',
            url: "/apply",
            data: {
                'days': days,
                'time': ttime + ' ' + amPM,
                'zone1length': zone1length,
                'zone2length': zone2length,
                'zone3length': zone3length
            }
        }
    ).done(function (data) {
            showMessages(data.message);
            if (days != '') {
                $('ul li:nth-child(2) span').html(days);
                flash($('#days'));
            }
            if (ttime != '') {
                $('ul li:nth-child(3) span').html(ttime + ' ' + amPM).val('');
                flash($('#ttime'));
                $('div#nextRunTime span').html(data.nextTime);
                fancyNextTime();
            }
            if (zone1length != '') {
                $('ul li:nth-child(4) span').html(zone1length).val('');
                flash($('#zone1length'));
            }
            if (zone2length != '') {
                $('ul li:nth-child(5) span').html(zone2length).val('');
                flash($('#zone2length'));
            }
            if (zone3length != '') {
                $('ul li:nth-child(6) span').html(zone3length).val('');
                flash($('#zone3length'));
            }
        })
}

function flash(tis) {
    $(tis).animate({backgroundColor: '#b6e026'}, 200, function () {
        $(this).val('').animate({backgroundColor: '#fff'}, 1000)
    })
}

function getLog(){
    $.ajax(
        {
            type: 'post',
            url: "/log"
        }
    ).done(function (data) {
            $('div#log').html('');
            for(var i = 0 ; i < data.log.length ; i++){
                if (data.log[i] === '-='){
                    $('#log').append("<div class='line'></div>");
                } else {
                    $('#log').append('<p>' + data.log[i] + '</p>')
                }

            }
        $('#fade').fadeIn(200);
        $('#light').fadeIn(200);
    })
}


$('#logButton').click(function () {
    getLog();
    getUptimeCount()
});

$('#logClose, #fade').click(function () {
    $('#fade').fadeOut(200);
    $('#light').fadeOut(200);
});


function showMessages(message) {
    if (message != ''){
        $('#messages').html(message).fadeIn(300).delay(5000).fadeOut(800);
    }
}


if (fullAuto) {
    $('#toggle').css({left: '28px'});
    $('#toggleBG').css({backgroundColor: '#b6e026'});
    $('.goAway').hide();
    $('ul li:nth-child(1) span').html(' True');
} else {
    $('#toggle').css({left: '2px'});
    $('#toggleBG').css({backgroundColor: '#bbb'});
    $('.goAway').show();
    $('ul li:nth-child(1) span').html(' False');
}

$('div#toggleBG').on('click', function () {
    fullAuto = !fullAuto;
    fullAutoFunc(fullAuto);
    getUptimeCount()
});


function fullAutoFunc(fullAuto) {
    $.ajax(
        {
            type: 'post',
            url: "/full_auto",
            data: {
                'full_auto': fullAuto
            }
        }
    ).done(function (data) {
            if (fullAuto) {
                $('#toggle').animate({left: '28px'}, 'fast');
                $('#toggleBG').animate({backgroundColor: '#b6e026'}, 'fast');
                $('.goAway').hide(500);
                $('ul li:nth-child(1) span').html(' True');
            } else {
                $('#toggle').animate({left: '2px'}, 'fast');
                $('#toggleBG').animate({backgroundColor: '#bbb'}, 'fast');
                $('.goAway').show(500);
                $('ul li:nth-child(1) span').html(' False');
            }
        })
}


var startStopVar = 'stop';

$('div#startButton').click(function(){
    if (startStopVar === 'start'){
        startStopVar = 'stop';
    } else if (startStopVar === 'stop') {
        startStopVar = 'start';
    }
    startStop(startStopVar);
    getUptimeCount()
});

function startStop(startStopVar){
    $.ajax(
        {
            type: 'post',
            url: "/start_stop",
            data: {
                'start_stop': startStopVar
            }
        }
    ).done(function (data) {
        showMessages(data.message);
        $("div#nextRunTime span").html(data.nextRunDate);
            if (startStopVar === 'start') {
                $('#startButton').addClass('stopButton').html('Stop');
                $('#system_on_off').switchClass('off', 'on');
            } else {
                $('#startButton').removeClass('stopButton').html('Start');
                $('#system_on_off').switchClass('on', 'off');
            }

        });
}

if(systemRunning){
    $('#startButton').addClass('stopButton').html('Stop');
    $('#system_on_off').switchClass('off', 'on');
} else {
    $('#startButton').removeClass('stopButton').html('Start');
    $('#system_on_off').switchClass('on', 'off');
}

var plsi, rt_plsi;

function getUptimeCount() {
    $.ajax(
        {
            type: 'post',
            url: "/uptime"
        }
    ).done(function (data) {
        $('div#uptime span').html(data.uptime);
        $('div#cycles span').html(data.count);
        $('div#nextRunTime span').html(data.next);
        fancyNextTime();
        if (parseFloat(data.rain) === 1.0) {
            plsi = 'inch'
        } else {
            plsi = 'inches'
        }
        if (parseFloat(data.rainTotal) === 1.0) {
            rt_plsi = 'inch'
        } else {
            rt_plsi = 'inches'
        }
        $('#rainTotals').html(data.rain + ' ' + plsi + ' of rain today & ' + data.rainTotal + ' ' + rt_plsi + ' since last run.')
    });
}

$('#uptime, #cycles').click(getUptimeCount);

 var months = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', "September", 'October', 'November', 'December'];

function fancyNextTime(){
    var dt = new Date();
    var $nt2 = $('div#nextRunTime span');
    var nt = $nt2.html();
    if (months[dt.getMonth()] === nt.split(' ')[1] && dt.getDate() === parseInt(nt.split(' ')[2])){
        if (parseInt(nt.split(' ')[4].split(':')[0]) > 6 && nt.split(' ')[5] === 'PM'){
            $nt2.html('Tonight at ' + nt.split(' ')[4] + ' ' + nt.split(' ')[5])
        } else {
            $nt2.html('Today at ' + nt.split(' ')[4] + ' ' + nt.split(' ')[5])
        }

    }
}

fancyNextTime();