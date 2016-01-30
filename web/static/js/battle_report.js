window.addEvent('domready', function() {
	'use strict';

	ykill.api(document.location.pathname, function(results) {
		var meta = results['meta'];
		$('meta').set('html', 'battle report for ' +
			ykill.format_system(meta, true) +
			' around ' + meta['kill_time']
		);

		var losses = [0, 0];
		['faction1', 'faction2', 'faction3'].each(function(faction, i) {
			var faction_div = $(faction);
			var members = results['factions'][i];
			members.each(function(char) {
				var row;
				if (char['death_id']) {
					var kill_url = '/kill/' + char['death_id'];
					row = new Element('a', {'href': kill_url, 'class': 'row'});
					row.addClass('dead');
				} else
					row = new Element('div', {'class': 'row'});

				var portraits_div = new Element('div', {'class': 'portraits'});
				portraits_div.adopt(
					new Element('div').adopt(
						ykill.portrait(char['ship_type_id'], char['ship_name'], 'Type', 32),
						new Element('div', {'class': 'tooltip', 'html': char['ship_name']})
					),
					new Element('div').adopt(
						ykill.portrait(char['corporation_id'], char['corporation_name'], 'Corporation', 32),
						new Element('div', {'class': 'tooltip', 'html': char['corporation_name']})
					)
				);
				if (char['alliance_id'])
					portraits_div.grab(
						new Element('div').adopt(
							ykill.portrait(char['alliance_id'], char['alliance_name'], 'Alliance', 32),
							new Element('div', {'class': 'tooltip', 'html': char['alliance_name']})
						)
					);
				row.grab(portraits_div);

				var text_div = new Element('div', {'class': 'text'});
				text_div.appendText(char['character_name'] + ' (' + char['ship_name'] + ')');
				text_div.grab(new Element('br'));
				if (char['alliance_id'])
					text_div.appendText(char['alliance_name']);
				else
					text_div.appendText(char['corporation_name']);
				row.grab(text_div);

				if ('cost' in char) {
					var cost_div = new Element('div', {'class': 'cost'});
					cost_div.appendText(ykill.format_millions(char['cost']));
					if (char['pod']) {
						cost_div.adopt(
							new Element('br'),
							new Element('a', {'href': '/kill/' + char['pod'], 'html': '[pod]'})
						);
					}
					row.grab(cost_div);
				}

				var damage_div = new Element('div', {'class': 'damage'});
				if (char['damage_dealt'])
					damage_div.appendText(ykill.format_number(char['damage_dealt']));
				row.grab(damage_div);

				faction_div.grab(row);

				if (char['cost'] && i < 2)
					losses[i] += char['cost'];
			});

			if (i == 2 && members.length)
				faction_div.setStyle('display', 'block'); // unhide third party
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
