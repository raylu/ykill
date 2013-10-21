Object.append(window.ykill, {
	'api': function (path, cb) {
		new Request.JSON({
			'url': ykill.api_host + path,
			'onSuccess': cb,
		}).get();
	},

	'portrait': function (id, text, img_dir, img_suffix) {
		var img = new Element('img', {
			'src': '//image.eveonline.com/' + img_dir + '/' + id + img_suffix,
			'alt': text,
		});
		return img;
	},
});
