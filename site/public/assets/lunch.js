(() => {
  const tabs = document.querySelector('[data-lunch-tabs]');
  if (!tabs) return;
  const buttons = [...tabs.querySelectorAll('[role="tab"]')];
  const panels = buttons.map(button => document.getElementById(button.getAttribute('aria-controls')));
  if (!buttons.length || panels.some(panel => !panel)) return;

  function select(index, focus = false) {
    buttons.forEach((button, i) => {
      const selected = i === index;
      button.setAttribute('aria-selected', String(selected));
      button.tabIndex = selected ? 0 : -1;
      panels[i].hidden = !selected;
    });
    if (focus) buttons[index].focus();
  }
  buttons.forEach((button, index) => {
    panels[index].setAttribute('role', 'tabpanel');
    panels[index].setAttribute('aria-labelledby', button.id);
    panels[index].tabIndex = 0;
    button.addEventListener('click', () => select(index));
    button.addEventListener('keydown', event => {
      let target = index;
      if (event.key === 'ArrowRight') target = (index + 1) % buttons.length;
      else if (event.key === 'ArrowLeft') target = (index + buttons.length - 1) % buttons.length;
      else if (event.key === 'Home') target = 0;
      else if (event.key === 'End') target = buttons.length - 1;
      else return;
      event.preventDefault();
      select(target, true);
    });
  });
  select(0);
  tabs.hidden = false;
})();
