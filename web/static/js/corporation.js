window.addEvent('domready', function() {
	var corp_id = document.location.pathname.split('/').getLast();
	ykill.api('/corporation/' + corp_id, function(kills) {
		var table = $('kills').getChildren('tbody')[0];
		kills.each(function(kill) {
			var tr = new Element('tr');

			var kill_time = kill['kill_time'].split(' ', 2);
			var a = new Element('a', {'href': '/kill/' + kill['kill_id']});
			a.appendText(kill_time[0]);
			a.adopt(new Element('br'));
			a.appendText(kill_time[1]);
			var td = new Element('td').adopt(a);
			tr.adopt(td);

			td = new Element('td');
			td.appendText(kill['system_name'] + ' ');
			td.adopt(new Element('span', {'html': kill['security'].toFixed(1)}));
			td.adopt(new Element('br'));
			td.appendText(kill['region']);
			tr.adopt(td);

			td = new Element('td');
			var victim = kill['victim'];
			show_portrait(td, victim['ship_type_id'], victim['ship_name'], 'type', '_32.png');
			show_portrait(td, victim['character_id'], victim['character_name'], 'character', '_32.jpg');
			if (victim['faction_id']) {
				show_portrait(td, victim['faction_id'], victim['faction_name'], 'faction', '_32.png');
			}
			tr.adopt(td);

			td = new Element('td');
			td.appendText(victim['character_name']);
			td.adopt(new Element('br'));
			td.appendText(victim['corporation_name']);
			if (victim['alliance_id'])
				td.appendText(' / ' + victim['alliance_name']);
			if (victim['faction_id'])
				td.appendText(' / ' + victim['faction_name']);
			tr.adopt(td);

			td = new Element('td');
			var final_blow = kill['final_blow'];
			show_portrait(td, final_blow['ship_type_id'], final_blow['ship_name'], 'type', '_32.png');
			show_portrait(td, final_blow['character_id'], final_blow['character_name'], 'character', '_32.jpg');
			if (final_blow['faction_id']) {
				show_portrait(td, final_blow['faction_id'], final_blow['faction_name'], 'faction', '_32.png');
			}
			tr.adopt(td);

			td = new Element('td');
			td.appendText(final_blow['character_name'] + ' (' + kill['attackers'] + ')');
			td.adopt(new Element('br'));
			td.appendText(final_blow['corporation_name']);
			if (final_blow['alliance_id'])
				td.appendText(' / ' + final_blow['alliance_name']);
			if (final_blow['faction_id'])
				td.appendText(' / ' + final_blow['faction_name']);
			tr.adopt(td);

			table.adopt(tr);
		});
	});

	function show_portrait(el, id, text, img_dir, img_suffix) {
		el.adopt(new Element('img', {
			'src': '//image.eveonline.com/' + img_dir + '/' + id + img_suffix,
			'alt': text,
		}));
	}
});
