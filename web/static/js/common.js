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

		'portrait': function(id, text, img_dir, size) {
			var extension = 'png';
			if (img_dir == 'Character')
				extension = 'jpg';
			var img = new Element('img', {
				'src': 'https://image.zkillboard.com/' + img_dir + '/' + id + '_' + size + '.' + extension,
				'alt': text,
				'width': size,
				'height': size,
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
		},

		'format_system': function(system, wh_info) {
			if (system['security_status'] == 'wspace')
				security = 'C' + system['wh_class'];
			else
				security = system['security'].toFixed(1);
			var system_info = system['system_name'] + ' <span class="' + system['security_status'] + '">' + security + '</span>';
			if (wh_info && system['wh_class']) {
				system_info += ' static ' + system['static1'];
				if (system['static2'])
					system_info += '/' + system['static2'];
				if (system['wh_effect'])
					system_info += ', ' + system['wh_effect'];
				else
					system_info += ', no effect';
			}
			return system_info;
		}
	});
})();
