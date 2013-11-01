window.addEvent('domready', function() {
	ykill.api(document.location.pathname, function(results) {
		var meta = results['meta'];
		$('meta').set('html', 'battle report for ' +
			ykill.format_system(meta, true) +
			' around ' + meta['kill_time']
		);

		var losses = [0, 0];
		['faction1', 'faction2', 'faction3'].each(function(faction, i) {
			var table = $(faction);
			var members = results['factions'][i];
			members.each(function(char) {
				var tr = new Element('tr');
				if (char['death_id']) {
					var kill_url = '/kill/' + char['death_id'];
					tr.addClass('dead');
					tr.addEvent('click', function(e) {
						if (e.target.tagName == 'A')
							return true;
						e.preventDefault();
						if (e.event.which == 2 || e.control) // 2: middle-click
							window.open(kill_url);
						else
							window.location = kill_url;
					});
				}

				var td = new Element('td');
				td.adopt(
					new Element('div').adopt(
						ykill.portrait(char['ship_type_id'], char['ship_name'], 'Type', 32),
						new Element('div', {'class': 'tooltip', 'html': char['ship_name']})
					),
					ykill.portrait(char['character_id'], char['character_name'], 'Character', 32),
					new Element('div').adopt(
						ykill.portrait(char['corporation_id'], char['corporation_name'], 'Corporation', 32),
						new Element('div', {'class': 'tooltip', 'html': char['corporation_name']})
					)
				);
				if (char['alliance_id'])
					td.grab(
						new Element('div').adopt(
							ykill.portrait(char['alliance_id'], char['alliance_name'], 'Alliance', 32),
							new Element('div', {'class': 'tooltip', 'html': char['alliance_name']})
						)
					);
				tr.grab(td);

				td = new Element('td');
				td.appendText(char['character_name']);
				if (char['pod']) {
					td.appendText(' ');
					td.adopt(new Element('a', {'href': '/kill/' + char['pod'], 'html': '[pod]'}));
				}
				td.grab(new Element('br'));
				if (char['alliance_id'])
					td.appendText(char['alliance_name']);
				else
					td.appendText(char['corporation_name']);
				tr.grab(td);

				td = new Element('td');
				if ('cost' in char)
					td.grab(new Element('a', {
						'href': kill_url, 'html': ykill.format_millions(char['cost'])
					}));
				tr.grab(td);

				table.grab(tr);

				if (char['cost'])
					losses[i] += char['cost'];
			});
			if (i == 2 && members.length)
				table.setStyle('display', 'table');
		});

		losses.each(function(lost, i) {
			var table = $('faction' + (i+1) + '_summary')
			table.grab(new Element('tr').adopt(
				new Element('td').appendText('losses'),
				new Element('td').appendText(ykill.format_billions(lost) + ' billion')
			));
			var killed = losses[1 - i];
			var efficiency = killed / (lost + killed);
			if (efficiency === efficiency)
				efficiency = (efficiency * 100).toFixed(0) + '%';
			else // NaN
				efficiency = 'n/a';
			table.grab(new Element('tr').adopt(
				new Element('td').appendText('efficiency'),
				new Element('td').appendText(efficiency)
			));
		});
	});
});
