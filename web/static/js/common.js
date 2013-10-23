(function() {
	var locale_options = false;
	try {
		(0).toLocaleString('i');
	} catch (e) { // https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Global_Objects/Number/toLocaleString#Example:_Checking_for_support_for_locales_and_options_arguments
		locale_options = e.name == 'RangeError';
	}
	Object.append(window.ykill, {
		'api': function(path, cb) {
			new Request.JSON({
				'url': ykill.api_host + path,
				'onSuccess': cb,
			}).get();
		},

		'portrait': function(id, text, img_dir, img_suffix) {
			var img = new Element('img', {
				'src': '//image.eveonline.com/' + img_dir + '/' + id + img_suffix,
				'alt': text,
			});
			return img;
		},

		'format_isk': function(isk) {
			isk /= 100;
			if (!locale_options)
				return parseFloat(isk.toFixed(0)).toLocaleString();
			return isk.toLocaleString('en-US', {'maximumFractionDigits': 0});
		},
		'format_millions': function(isk) {
			isk /= 100 * 1000 * 1000;
			if (!locale_options)
				return parseFloat(isk.toFixed(2)).toLocaleString();
			return isk.toLocaleString('en-US', {'minimumFractionDigits': 2, 'maximumFractionDigits': 2});
		},
		'format_billions': function(isk) {
			return ykill.format_millions(isk / 1000);
		}
	});
})();
