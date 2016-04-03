(function() {
	'use strict';

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
				'onFailure': function(xhr) {
					$('wrapper').empty().grab(new Element('div', {
						'class': 'error',
						'html': 'as you pass through the wormhole you realize that it collapses behind you.' +
							'<br>have you become trapped?'
					}));
				},
				'onComplete': function() {
					var loading = $('loading');
					if (loading)
						loading.setStyle('display', 'none');
				},
			}).get();
		},

		'imageserver': 'https://imageserver.eveonline.com',

		'portrait': function(id, text, img_dir, size) {
			var extension = 'png';
			if (img_dir == 'Character')
				extension = 'jpg';
			var img = new Element('img', {
				'src': ykill.imageserver + '/' + img_dir + '/' + id + '_' + size + '.' + extension,
				'alt': text,
				'width': size,
				'height': size,
			});
			return img;
		},

		'format_number': function(number) {
			if (!locale_options)
				return parseFloat(number.toFixed()).toLocaleString();
			return number.toLocaleString('en-US', {'maximumFractionDigits': 0});
		},
		'format_isk': function(isk) {
			return ykill.format_number(isk / 100);
		},
		'format_millions': function(isk) {
			isk /= 100 * 1000 * 1000;
			if (!locale_options)
				return parseFloat(isk.toFixed(2)).toLocaleString();
			return isk.toLocaleString('en-US', {'minimumFractionDigits': 2, 'maximumFractionDigits': 2});
		},
		'format_billions': function(isk) {
			return ykill.format_millions(isk / 1000);
		},

		'format_system': function(system, wh_info) {
			var security;
			if (system['security_status'] == 'wspace')
				security = 'C' + system['wh_class'];
			else if (system['security'] > 0.0 && system['security'] < 0.1)
				security = 0.1
			else
				security = system['security'].toFixed(1);
			var system_info = system['system_name'] + ' <span class="' + system['security_status'] + '">' + security + '</span>';
			if (wh_info && system['wh_class']) {
				if (system['static1']) {
					system_info += ' static ' + system['static1'];
					if (system['static2'])
						system_info += '/' + system['static2'];
				} else
					system_info += ' no statics';
				if (system['wh_effect'])
					system_info += ', ' + system['wh_effect'];
				else
					system_info += ', no effect';
			}
			return system_info;
		}
	});
})();
