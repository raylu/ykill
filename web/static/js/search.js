window.addEvent('domready', function() {
	document.title += ' - search';
	ykill.api('/search' + document.location.search, function(results) {
		var wrapper = $('wrapper');
		Object.each(results, function(list, key) {
			if (!list.length)
				return;
			var div = new Element('div').grab(
				new Element('h2', {'html': key[0].toUpperCase() + key.substr(1)})
			);
			var key_singular = key.substr(0, key.length-1)
			var name_key = key_singular + '_name';
			var id_key = key_singular + '_id';
			list.each(function(entity) {
				div.adopt(
					new Element('a', {
						'html': entity[name_key],
						'href': '/' + key_singular + '/' + entity[id_key],
					}),
					new Element('br')
				);
			});
			wrapper.grab(div);
		});
		if (!wrapper.getElements('div').length)
			wrapper.grab(new Element('div').addClass('no_results').appendText('no search results'));
	});
});
