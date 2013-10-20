window.ykill.api = function (path, cb) {
	new Request.JSON({
		'url': ykill.api_host + path,
		'onSuccess': cb,
	}).get();
}
