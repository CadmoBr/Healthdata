select
      count(*) as failures,
      count(*) != 0 as should_warn,
      count(*) != 0 as should_error
    from (
      
    
    



select sk_date
from "healthdata_dw"."dw_gold"."dim_date"
where sk_date is null



      
    ) dbt_internal_test