window.addEvent('domready', function() {
	ykill.api('/search' + document.location.search, function(results) {
		var corps = $('corps');
		results.corporations.each(function(corp) {
			corps.grab(new Element('a', {
				'html': corp.corporation_name,
				'href': '/corporation/' + corp.corporation_id,
			}));
		});
	});
});
