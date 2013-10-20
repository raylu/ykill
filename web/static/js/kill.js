window.addEvent('domready', function() {
	var kill_id = document.location.pathname.split('/').getLast();
	ykill.api('/kill/' + kill_id, function(data) {
		var kill = data.kill;
		$('kill_time').appendText(kill['kill_time']);
		$('solar_system').appendText(kill['solarSystemName'] + ' (' + kill['security'].toFixed(1) + ')');

		var div = $('characters');
		data.characters.each(function(char) {
			div.adopt(new Element('img', {
				'src': '//image.eveonline.com/Character/' + char['character_id'] + '_64.jpg',
				'alt': char['character_name'],
			}));
			div.appendText(char['character_name']);
			div.adopt(new Element('img', {
				'src': '//image.eveonline.com/Corporation/' + char['corporation_id'] + '_64.png',
				'alt': char['corporation_name'],
			}));
			div.appendText(char['corporation_name']);
			if (char['alliance_id']) {
				div.adopt(new Element('img', {
					'src': '//image.eveonline.com/Alliance/' + char['alliance_id'] + '_64.png',
					'alt': char['alliance_name'],
				}));
				div.appendText(char['alliance_name']);
			}
			div.adopt(new Element('br'));
		});
	});
});
