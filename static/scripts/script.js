$('.manButt').on('click', function () {
    GetURL($(this).attr('id'))
});

function GetURL(number) {
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

$('#applyButton').click(apply);

function apply() {
    var days = $('#days').val();
    var ttime = $('#ttime').val();
    var zone1length = $('#zone1length').val();
    var zone2length = $('#zone2length').val();
    var zone3length = $('#zone3length').val();
    $.ajax(
        {
            type: 'post',
            url: "/apply",
            data: {
                'days': days,
                'time': ttime,
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
                $('ul li:nth-child(3) span').html(ttime).val('');
                flash($('#ttime'));
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


$('#logButton').click(function () {
    $('#fade').fadeIn(200);
    $('#light').fadeIn(200);
});

$('#logClose, #fade').click(function () {
    $('#fade').fadeOut(200);
    $('#light').fadeOut(200);
});


function showMessages(message) {
    if (message != ''){
        $('#messages').html(message).fadeIn(300).delay(10000).fadeOut(800);
    }
}


if (fullAuto) {
    $('#toggle').animate({left: '28px'});
    $('#toggleBG').animate({backgroundColor: '#b6e026'});
    $('.goAway').hide(500);
    $('ul li:nth-child(1) span').html(' True');
} else {
    $('#toggle').animate({left: '2px'});
    $('#toggleBG').animate({backgroundColor: '#bbb'});
    $('.goAway').show(500);
    $('ul li:nth-child(1) span').html(' False');
}

$('div#toggleBG').on('click', function () {
    fullAuto = !fullAuto;
    fullAutoFunc(fullAuto);

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
