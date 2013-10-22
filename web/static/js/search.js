window.addEvent('domready', function() {
	document.title += ' - search';
	ykill.api('/search' + document.location.search, function(results) {
		var corps = $('corps');
		results.corporations.each(function(corp) {
			corps.adopt(
				new Element('a', {
					'html': corp.corporation_name,
					'href': '/corporation/' + corp.corporation_id,
				}),
				new Element('br')
			);
		});
	});
});
