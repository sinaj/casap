
$(document).ready(function () {
    var xhr = null;
    var currSpinner = null;
    $(".time_picker").datetimepicker();

    // FOR NAVIGATION BUTTONS AT TOP OF PAGE
    $(document).on('click', '#people', function () {
        if (xhr != null){
            xhr.abort();
        }
        xhr = $.ajax({
            url: "/get_people_table/",
            traditional: true,
            type: "GET",
            dataType: "json",
            data: {
                hash: 'something'
            },
            success: function (data) {
                //console.log(data['html'])
                $('.report-content').html(data['html']);
                $('.report-content').show();
                xhr = null;

            },
            failure: function (data) {
                console.log('Got an error when requesting show_people_table');
            }
        });
    });
    
    // FOR PEOPLE TABLE BUTTONS
    $(document).on('click', '.map', function () {
        if (xhr != null){
            xhr.abort();
            if (currSprinner!= null){
                currSprinner.css("opacity", 0);
            }
        }
        currSprinner = $(this).siblings('#cog');
        currSprinner.css("opacity", 1);
        //$(location).attr('href',"/map/");
        xhr = $.ajax({
            url: "/map/",
            traditional: true,
            async: true,
            type: "GET",
            dataType: "json",
            data: {
                person_hash: $(this).data('id')
            },
            success: function (data) {
                //console.log(data['html'])
                currSprinner.css("opacity", 0);
                currSprinner = null;
                $('.report-content').html(data['html']);
                xhr = null;
                
            },
            failure: function (data) {
                console.log('Got an error when requesting map');
            }
        });
    });

    $(document).on('click', '.calendar', function () {
        if (xhr != null){
            xhr.abort();
        }
        //$(location).attr('href',"/calendar/");
         xhr = $.ajax({
            url: "/calendar/",
            traditional: true,
            type: "GET",
            dataType: "json",
            data: {
                person_hash: $(this).data('id')
            },
            success: function (data) {
                //console.log(data['html'])
                $('.report-content').html(data['html']);
                xhr = null;
                
            },
            failure: function (data) {
                console.log('Got an error when requesting calendar');
            }
        });
    });

    $(document).on('click', '.circles', function () {
        if (xhr != null){
            xhr.abort();
        }
        //$(location).attr('href',"/calendar/");
         xhr = $.ajax({
            url: "/circles/",
            traditional: true,
            type: "GET",
            dataType: "json",
            data: {
                person_hash: $(this).data('id')
            },
            success: function (data) {
                //console.log(data['html'])
                $('.report-content').html(data['html']);
                xhr = null;
                
            },
            failure: function (data) {
                console.log('Got an error when requesting circles');
            }
        });
    });

    $(document).on('click', '.relation-clicked', function () {
        if (xhr != null){
            xhr.abort();
        }
        xhr = $.ajax({
            url: "/get_relations_table/",
            traditional: true,
            type: "GET",
            dataType: "json",
            data: {
                person_hash: $(this).data('id')
            },
            success: function (data) {
                $('.relation-table').html(data['html']);
                xhr = null;
            },
            failure: function (data) {
                console.log('Got an error when requesting relations');
            }
        });
    });

    
    // FOR AUTO COMPLETE AJAX REQUEST LOCATION SEARCH ON ACTIVITY HOMEPAGE
    $(document).on('focus', '#selectlocation', function () {
    //function searchLocation(){
        $("#selectlocation").autocomplete({
            source: "/get_loc_search/",
            minLength: 1,
        });
    });
});
