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
		var kills = $('kills');
		data['kills'].each(function(kill) {
			var row = new Element('a', {'href': '/kill/' + kill['kill_id'], 'class': 'row'});

			var kill_time = kill['kill_time'].split(' ', 2);
			var div = new Element('div');
			div.appendText(kill_time[0]);
			div.grab(new Element('br'));
			div.appendText(kill_time[1]);
			row.grab(div);

			div = new Element('div', {'html': ykill.format_system(kill, false)});
			div.grab(new Element('br'));
			if (kill['wh_class']) {
				if (kill['static1']) {
					div.appendText('static ' + kill['static1']);
					if (kill['static2'])
						div.appendText('/' + kill['static2']);
				} else
					div.appendText('no statics');
			} else
				div.appendText(kill['region']);
			row.grab(div);

			div = new Element('div');
			var victim = kill['victim'];
			div.adopt(
				ykill.portrait(victim['ship_type_id'], victim['ship_name'], 'Type', 32),
				ykill.portrait(victim['character_id'], victim['character_name'], 'Character', 32)
			);
			row.grab(div);

			div = new Element('div');
			div.appendText(victim['character_name'] + ' (' + victim['ship_name'] + ')');
			div.grab(new Element('br'));
			div.appendText(victim['corporation_name']);
			if (victim['alliance_id'])
				div.appendText(' / ' + victim['alliance_name']);
			if (victim['faction_id'])
				div.appendText(' / ' + victim['faction_name']);
			row.grab(div);

			div = new Element('div');
			var final_blow = kill['final_blow'];
			div.adopt(
				ykill.portrait(final_blow['ship_type_id'], final_blow['ship_name'], 'Type', 32),
				ykill.portrait(final_blow['character_id'], final_blow['character_name'], 'Character', 32)
			);
			row.grab(div);

			div = new Element('div');
			var attacker_name = final_blow['character_name'] || final_blow['ship_name'];
			div.appendText(attacker_name + ' (' + kill['attackers'] + ')');
			div.grab(new Element('br'));
			div.appendText(final_blow['corporation_name']);
			if (final_blow['alliance_id'])
				div.appendText(' / ' + final_blow['alliance_name']);
			if (final_blow['faction_id'])
				div.appendText(' / ' + final_blow['faction_name']);
			row.grab(div);

			div = new Element('div');
			div.appendText(ykill.format_millions(kill['cost']));
			if (victim[entity_type + '_id'] == entity_id)
				div.addClass('loss');
			row.grab(div);

			kills.grab(row);
		});

		var page = Number(search.substr(6) || 1);
		var pages = $('pages');
		pages.grab(new Element('a', {'html': 'next', 'href': path + '?page=' + (page + 1)}), 'top');
		if (page > 1)
			pages.grab(new Element('a', {'html': 'prev', 'href': path + '?page=' + (page - 1)}), 'top');
	});
});
