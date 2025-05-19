import logging
_logger = logging.getLogger(__name__)

def get_next_sequence_number(base_sequence, is_payment, last_number, journal_id, move_type):
    new_number = last_number + 1
    new_sequence = "%s/%04d" % (base_sequence, new_number)

    # Simpan prefix sementara
    prefix = ""
    if journal_id.refund_sequence and move_type in ('out_refund', 'in_refund'):
        prefix = "R"
    elif journal_id.payment_sequence and is_payment:
        prefix = "P"

    # Gabungkan prefix dengan sequence tanpa mengganggu format
    new_sequence = "%s%s" % (prefix, new_sequence)

    _logger.info("New Sequence Generated: %s", new_sequence)
    print("new_number", new_number)
    print("new_sequence", new_sequence)
    print("new_sequence[3:]", new_sequence[3:])

    return new_sequence
