def seed_demo_data(store):
    store.reset_graph()
    accounts = [
        ("A100", "Asha Mehta", 78), ("A101", "Rohan Shah", 22),
        ("A102", "Neel Patel", 64), ("A103", "Mira Joshi", 12),
        ("A104", "Dev Kumar", 83), ("A105", "Ira Singh", 18),
    ]
    for account_id, name, score in accounts:
        store.add_account(account_id, name, score)
    uses = [
        ("A100", "D-77", "Android"), ("A102", "D-77", "Android"),
        ("A104", "D-77", "Android"), ("A101", "D-12", "iOS"),
        ("A103", "D-22", "Windows"), ("A105", "D-35", "Android"),
    ]
    for account_id, device_id, kind in uses:
        store.add_device_use(account_id, device_id, kind)
    txs = [
        ("T9001", 120.00, "completed", "2026-10-16T10:02:00", "A100", "A101", "D-77"),
        ("T9002", 4800.00, "pending_review", "2026-10-16T10:05:00", "A100", "A102", "D-77"),
        ("T9003", 9900.00, "pending_review", "2026-10-16T10:07:00", "A104", "A102", "D-77"),
        ("T9004", 75.00, "completed", "2026-10-16T11:20:00", "A101", "A103", "D-12"),
        ("T9005", 7200.00, "declined", "2026-10-16T11:22:00", "A102", "A104", "D-77"),
        ("T9006", 45.00, "completed", "2026-10-16T12:15:00", "A105", "A103", "D-35"),
    ]
    for tx in txs:
        store.add_transaction(*tx)
    store.add_account_link("A100", "A102", "shared device")
    store.add_account_link("A102", "A104", "shared device")
