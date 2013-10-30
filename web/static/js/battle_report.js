window.addEvent('domready', function() {
	ykill.api(document.location.pathname, function(results) {
		['faction1', 'faction2'].each(function(faction, i) {
			var table = $(faction);
			results[i].each(function(char) {
				var tr = new Element('tr');
				if (char['death_id']) {
					tr.addClass('dead');
					tr.addEvent('click', function() {
						window.location = '/kill/' + char['death_id'];
					});
				}

				td = new Element('td').grab(
					new Element('div').adopt(
						ykill.portrait(char['ship_type_id'], char['ship_name'], 'Type', 32),
						new Element('div', {'class': 'tooltip', 'html': char['ship_name']})
					)
				);
				td.grab(ykill.portrait(char['character_id'], char['character_name'], 'Character', 32));
				td.grab(
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
				td.grab(new Element('br'));
				if (char['alliance_id'])
					td.appendText(char['alliance_name']);
				else
					td.appendText(char['corporation_name']);
				tr.grab(td);

				table.grab(tr);
			});
		});
	});
});
