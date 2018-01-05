var app = angular.module('App', []);

app.config(function ($interpolateProvider) {
    $interpolateProvider.startSymbol('[[');
    $interpolateProvider.endSymbol(']]');
});

app.controller('Ctrl', ['$scope', function ($scope) {

    $scope.safeApply = function (fn) {
        var phase = this.$root.$$phase;
        if (phase == '$apply' || phase == '$digest') {
            if (fn && (typeof(fn) === 'function')) {
                fn();
            }
        } else {
            this.$apply(fn);
        }
    };

    init_service_ctrl($scope);

    $scope.addAddress = function () {
        $scope.addresses.push({
            errors: [],
            instance_id: undefined,
            value: "",
        })
    }

    $scope.removeAddress = function (index) {
        $scope.addresses.splice(index, 1);
    }

}]);

var init_service_ctrl = function ($scope) {
    $scope.addresses = $.addresses;
    $scope.safeApply();
    s = $scope;
}