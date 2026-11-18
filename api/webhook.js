// Legacy implementation is preserved under disabled/commerce/api/.
module.exports = (req, res) => res.status(410).json({ error: 'Zahlungen und Credits sind deaktiviert.' });
