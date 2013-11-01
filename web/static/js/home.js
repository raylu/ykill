window.addEvent('domready', function() {
	var table = $('expensive');
	ykill.api('/top/cost', function(kills) {
		kills.each(function(kill) {
			table.grab(new Element('tr').adopt(
				new Element('td', {'html': kill['kill_time'].substr(5)}),
				new Element('td').grab(ykill.portrait(kill['ship_type_id'], kill['ship_name'], 'Type', 32)),
				new Element('td', {'html': kill['ship_name']}),
				new Element('td', {'html': ykill.format_system(kill, false)}),
				new Element('td').grab(
					new Element('a', {
						'href': '/kill/' + kill['kill_id'],
						'html': ykill.format_billions(kill['cost'])
					})
				)
			));
		});
	});
});
