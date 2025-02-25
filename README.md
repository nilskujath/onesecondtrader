# OneSecondTrader

## Installation

### Git

```shell
git clone https://github.com/nilskujath/onesecondtrader.git
```

## Notes

When replaying data from a csv file with `datafeeds.replay_from_csv`: The CSV file must adhere to the conventions in the table below. Additional columns will be ignored and won't cause an error. A missing column will cause an error.

```
COLUMN      VALUE TYPE

ts_event    uint64_t
open        int64_t
high        int64_t
low         int64_t
close       int64_t
volume      uint64_t
symbol      str
```

This convention is based on [DataBento's conventions](https://databento.com/docs/standards-and-conventions/common-fields-enums-types#timestamps?historical=python&live=python&reference=python), which seem sensible.