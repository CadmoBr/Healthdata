
    
    

select
    sk_fact_beds as unique_field,
    count(*) as n_records

from "healthdata_dw"."dw_gold"."fact_hospital_beds"
where sk_fact_beds is not null
group by sk_fact_beds
having count(*) > 1


