window.addEvent('domready', function() {
	var path = document.location.pathname;
	var search = document.location.search;
	var split = path.split('/');
	var entity_type = split[1];
	var entity_id = split[2];
	ykill.api(path + search, function(data) {
		var entity_name = data['stats'][entity_type + '_name'];
		document.title += ' - ' + entity_name;
		var base_path = '/' + entity_type + '/' + entity_id;
		$('entity_name').grab(new Element('a', {'href': base_path, 'html': entity_name}));

		if ('killed' in data['stats']) {
			var table = $('stats');
			table.adopt(
				new Element('tr').adopt(
					new Element('td', {'html': '<a href="' + base_path + '/kills' + '">killed</a>:'}),
					new Element('td', {'html': ykill.format_billions(data['stats']['killed']) + ' billion'})
				),
				new Element('tr').adopt(
					new Element('td', {'html': '<a href="' + base_path + '/losses' + '">lost</a>:'}),
					new Element('td', {'html': ykill.format_billions(data['stats']['lost']) + ' billion'})
				)
			);
		}

		if (entity_type == 'ship')
			entity_type = 'ship_type';
		table = $('kills').getChildren('tbody')[0];
		data['kills'].each(function(kill) {
			var tr = new Element('tr');

			var kill_time = kill['kill_time'].split(' ', 2);
			var a = new Element('a', {'href': '/kill/' + kill['kill_id']});
			a.appendText(kill_time[0]);
			a.grab(new Element('br'));
			a.appendText(kill_time[1]);
			var td = new Element('td').grab(a);
			tr.grab(td);

			td = new Element('td', {'html': ykill.format_system(kill, false)});
			td.grab(new Element('br'));
			if (kill['wh_class']) {
				td.appendText('static ' + kill['static1']);
				if (kill['static2'])
					td.appendText('/' + kill['static2']);
			} else
				td.appendText(kill['region']);
			tr.grab(td);

			td = new Element('td');
			var victim = kill['victim'];
			td.adopt(
				ykill.portrait(victim['ship_type_id'], victim['ship_name'], 'Type', 32),
				ykill.portrait(victim['character_id'], victim['character_name'], 'Character', 32)
			);
			tr.grab(td);

			td = new Element('td');
			td.appendText(victim['character_name'] + ' (' + victim['ship_name'] + ')');
			td.grab(new Element('br'));
			td.appendText(victim['corporation_name']);
			if (victim['alliance_id'])
				td.appendText(' / ' + victim['alliance_name']);
			if (victim['faction_id'])
				td.appendText(' / ' + victim['faction_name']);
			tr.grab(td);

			td = new Element('td');
			var final_blow = kill['final_blow'];
			td.adopt(
				ykill.portrait(final_blow['ship_type_id'], final_blow['ship_name'], 'Type', 32),
				ykill.portrait(final_blow['character_id'], final_blow['character_name'], 'Character', 32)
			);
			tr.grab(td);

			td = new Element('td');
			var attacker_name = final_blow['character_name'] || final_blow['ship_name'];
			td.appendText(attacker_name + ' (' + kill['attackers'] + ')');
			td.grab(new Element('br'));
			td.appendText(final_blow['corporation_name']);
			if (final_blow['alliance_id'])
				td.appendText(' / ' + final_blow['alliance_name']);
			if (final_blow['faction_id'])
				td.appendText(' / ' + final_blow['faction_name']);
			tr.grab(td);

			td = new Element('td');
			td.appendText(ykill.format_millions(kill['cost']));
			if (victim[entity_type + '_id'] == entity_id)
				td.addClass('loss');
			tr.grab(td);

			table.grab(tr);
		});

		var page = Number(search.substr(6) || 1);
		var pages = $('pages');
		pages.grab(new Element('a', {'html': 'next', 'href': path + '?page=' + (page + 1)}), 'top');
		if (page > 1)
			pages.grab(new Element('a', {'html': 'prev', 'href': path + '?page=' + (page - 1)}), 'top');
	});
});
